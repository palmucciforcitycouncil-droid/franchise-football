# app/services/contracts.py
from __future__ import annotations
from typing import Dict, Any, List, Tuple
import random
from sqlmodel import Session, select, delete, SQLModel, Field, and_, UniqueConstraint
from app.models.contracts import Contract
from app.models.cap import TeamCap
from app.models.core_min import Player
from app.models.season_stats import TeamSeasonStats

DEFAULT_CAP_LIMIT = 2000  # cap units per team-season (AAV units)

class FreeAgentBid(SQLModel, table=True):
    __tablename__ = "free_agent_bids"
    id: int | None = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    player_id: int = Field(index=True)
    team_id: int = Field(index=True)
    aav: int = 0
    years: int = 1

def contract_active_in_season(c: Contract, season: int) -> bool:
    return c.status == "active" and c.start_season <= season <= c.end_season

def team_contracts_in_season(session: Session, team_id: int, season: int) -> List[Contract]:
    rows = session.exec(select(Contract).where(Contract.team_id == team_id, Contract.status == "active")).all()
    return [c for c in rows if contract_active_in_season(c, season)]

def team_cap_used(session: Session, team_id: int, season: int) -> int:
    return sum(c.aav for c in team_contracts_in_season(session, team_id, season))

def team_cap_space(session: Session, team_id: int, season: int, cap_limit: int = DEFAULT_CAP_LIMIT) -> int:
    return cap_limit - team_cap_used(session, team_id, season)

def compute_and_persist_team_cap(session: Session, team_id: int, season: int, cap_limit: int = DEFAULT_CAP_LIMIT) -> TeamCap:
    used = team_cap_used(session, team_id, season)
    row = session.exec(select(TeamCap).where(TeamCap.team_id == team_id, TeamCap.season == season)).first()
    if not row:
        row = TeamCap(team_id=team_id, season=season)
    row.cap_limit = cap_limit
    row.cap_used = used
    session.add(row)
    session.commit()
    session.refresh(row)
    return row

def expire_contracts(session: Session, season: int) -> Dict[str, int]:
    """
    Expire contracts that ended last season, and push those players to FA (team_id=None) if they have no other active deal.
    """
    expired = 0
    moved_to_fa = 0
    rows = session.exec(select(Contract).where(Contract.status == "active")).all()
    for c in rows:
        if c.end_season < season:
            c.status = "expired"
            session.add(c)
            expired += 1
            # If player has no other active for this season and is on a team, set team_id=None
            others = session.exec(
                select(Contract).where(Contract.player_id == c.player_id, Contract.status == "active")
            ).all()
            has_active = any(contract_active_in_season(o, season) for o in others)
            p = session.get(Player, c.player_id)
            if p and not has_active and getattr(p, "team_id", None) is not None:
                p.team_id = None
                session.add(p)
                moved_to_fa += 1
    session.commit()
    return {"expired": expired, "moved_to_fa": moved_to_fa}

def list_free_agents(session: Session, season: int) -> List[Player]:
    """
    Free agent definition (MVP): player has team_id is None AND has no active contract for given season.
    """
    players = session.exec(select(Player)).all()
    out: List[Player] = []
    for p in players:
        if getattr(p, "team_id", None) is not None:
            continue
        has_active = session.exec(select(Contract).where(Contract.player_id == getattr(p,"player_id",getattr(p,"id")), Contract.status=="active")).all()
        if any(contract_active_in_season(c, season) for c in has_active):
            continue
        out.append(p)
    return out

# --- Free agency bidding ---

def submit_bid(session: Session, season: int, team_id: int, player_id: int, aav: int, years: int) -> Dict[str, Any]:
    """
    Upsert team's bid for a player in a season.
    """
    row = session.exec(select(FreeAgentBid).where(
        FreeAgentBid.season==season, FreeAgentBid.player_id==player_id, FreeAgentBid.team_id==team_id
    )).first()
    if not row:
        row = FreeAgentBid(season=season, team_id=team_id, player_id=player_id)
    row.aav = max(80, int(aav))
    row.years = max(1, min(5, int(years)))
    session.add(row); session.commit()
    return {"status":"ok","bid_id":row.id}

def _player_market_score(p: Player) -> int:
    """
    Simple market desirability proxy: overall (if exists) + potential/2.
    """
    ov = int(getattr(p, "overall", 70) or 70)
    pot = int(getattr(p, "potential", 70) or 70)
    return ov + pot//2

def simulate_free_agency(session: Session, season: int, seed: int = 2025, cap_limit: int = DEFAULT_CAP_LIMIT) -> Dict[str, Any]:
    """
    Resolve all bids:
      - For each player in FA with bids, pick the winning team among those with cap space.
      - Winner is highest (aav, years, team_cap_space, random_tiebreak) weighted in that order.
      - Sign a Contract (status=active), set player.team_id, recompute cap for winner.
      - Idempotent: if player already on a team or has active contract in season, skip.
    """
    rng = random.Random(seed)
    signings = 0
    skipped_no_cap = 0
    skipped_already_signed = 0

    # Build FA set
    fa_players = list_free_agents(session, season)
    bids = session.exec(select(FreeAgentBid).where(FreeAgentBid.season==season)).all()
    by_player: dict[int, list[FreeAgentBid]] = {}
    for b in bids:
        by_player.setdefault(b.player_id, []).append(b)

    for p in fa_players:
        pid = getattr(p,"player_id",getattr(p,"id"))
        pbids = by_player.get(pid, [])
        if not pbids:
            continue
        # If already signed somehow, skip
        if getattr(p, "team_id", None) is not None:
            skipped_already_signed += 1
            continue
        active = session.exec(select(Contract).where(Contract.player_id==pid, Contract.status=="active")).all()
        if any(contract_active_in_season(c, season) for c in active):
            skipped_already_signed += 1
            continue

        # Consider only teams with sufficient cap for first-year AAV
        viable: list[tuple[FreeAgentBid,int]] = []
        for b in pbids:
            space = team_cap_space(session, b.team_id, season, cap_limit)
            if space >= b.aav:
                viable.append((b, space))
        if not viable:
            skipped_no_cap += 1
            continue

        # Choose winner: max by (aav, years, cap_space, rnd), deterministic seed
        rnd = rng.randint(0, 999)
        viable.sort(key=lambda t: (t[0].aav, t[0].years, t[1], rnd), reverse=True)
        win = viable[0][0]

        # Sign
        newc = Contract(
            player_id=pid,
            team_id=win.team_id,
            start_season=season,
            years=win.years,
            aav=win.aav,
            is_rookie=False,
            status="active"
        )
        session.add(newc)
        # Update player team
        p.team_id = win.team_id
        session.add(p)
        session.commit()
        # Recompute cap
        compute_and_persist_team_cap(session, win.team_id, season, cap_limit)
        signings += 1

    return {"signings": signings, "skipped_no_cap": skipped_no_cap, "skipped_already_signed": skipped_already_signed}

# ---------- Auto-cap initialization ----------

def init_season_cap_for_all_teams(session: Session, season: int, cap_limit: int = DEFAULT_CAP_LIMIT) -> Dict[str, int]:
    """
    Create/refresh TeamCap rows for every team that appears in TeamSeasonStats
    (or that already has at least one active contract) for the given season.
    Idempotent: updates existing rows.
    """
    # discover teams from stats and/or contracts
    stats_teams = {r.team_id for r in session.exec(select(TeamSeasonStats.team_id).where(TeamSeasonStats.season == season)).all()}
    # also include any team that already has a contract (useful in pre-season)
    contract_teams = {c.team_id for c in session.exec(select(Contract).where(Contract.status=="active")).all()}
    teams = sorted(stats_teams | contract_teams)

    created_or_updated = 0
    for tid in teams:
        compute_and_persist_team_cap(session, tid, season, cap_limit)
        created_or_updated += 1
    return {"teams": len(teams), "rows_written": created_or_updated}

# ---------- Re-sign (exclusive window) ----------

class ReSignOffer(SQLModel, table=True):
    """
    Exclusive re-sign offers: only the CURRENT team can offer a new deal that starts at `season`.
    Uniqueness: one offer per (season, player_id) to keep it simple; later we can store history if needed.
    """
    __tablename__ = "resign_offers"
    __table_args__ = (UniqueConstraint("season","player_id", name="uq_resign_player_season"),)

    id: int | None = Field(default=None, primary_key=True)
    season: int = Field(index=True)         # next season the new contract would start
    player_id: int = Field(index=True)
    team_id: int = Field(index=True)        # must equal player's current team
    aav: int = 0
    years: int = 1

def resign_candidates(session: Session, season: int) -> list[tuple[Player, Contract]]:
    """
    Players whose current contract ends at season-1 and is active.
    """
    prev = season - 1
    rows = session.exec(select(Contract).where(Contract.status=="active")).all()
    out: list[tuple[Player, Contract]] = []
    for c in rows:
        if c.end_season == prev:
            p = session.get(Player, c.player_id)
            if not p: 
                continue
            # player must still be on that team
            if getattr(p, "team_id", None) == c.team_id:
                out.append((p, c))
    return out

def submit_resign_offer(session: Session, season: int, team_id: int, player_id: int, aav: int, years: int) -> Dict[str, Any]:
    """
    Upsert a re-sign offer. Validates exclusivity (must be player's current team and an expiring contract).
    """
    p = session.get(Player, player_id)
    if not p:
        raise ValueError("Player not found")

    # Must be on this team now
    if getattr(p, "team_id", None) != team_id:
        raise ValueError("Exclusive window: only current team may offer")

    # Must be expiring at season-1
    prev = season - 1
    current = session.exec(select(Contract).where(Contract.player_id==player_id, Contract.status=="active")).all()
    if not any(c.end_season == prev and c.team_id == team_id for c in current):
        raise ValueError("No expiring contract for this player with this team")

    # Idempotent upsert
    row = session.exec(select(ReSignOffer).where(ReSignOffer.season==season, ReSignOffer.player_id==player_id)).first()
    if not row:
        row = ReSignOffer(season=season, player_id=player_id, team_id=team_id)
    row.aav = max(80, int(aav))
    row.years = max(1, min(5, int(years)))
    session.add(row); session.commit()
    return {"status":"ok","offer_id": row.id}

def simulate_resign_window(session: Session, season: int, cap_limit: int = DEFAULT_CAP_LIMIT) -> Dict[str, Any]:
    """
    For each resign candidate, if there's an offer and the team has cap space for season,
    sign a new contract that starts at `season`. Idempotent: if contract exists (start_season==season), skip.
    """
    signed = 0
    skipped_no_offer = 0
    skipped_no_cap = 0
    skipped_already_signed = 0

    cand = resign_candidates(session, season)
    # Precompute cap rows for all teams (auto-cap makes this idempotent)
    init_season_cap_for_all_teams(session, season, cap_limit)

    for (p, oldc) in cand:
        pid = getattr(p, "player_id", getattr(p, "id", None))
        # Already has a contract starting at season?
        existing = session.exec(select(Contract).where(
            Contract.player_id==pid, Contract.status=="active", Contract.start_season==season
        )).first()
        if existing:
            skipped_already_signed += 1
            continue

        offer = session.exec(select(ReSignOffer).where(ReSignOffer.season==season, ReSignOffer.player_id==pid)).first()
        if not offer:
            skipped_no_offer += 1
            continue
        if offer.team_id != getattr(p,"team_id",None):
            # safety check: must match current team
            skipped_no_offer += 1
            continue

        space = team_cap_space(session, offer.team_id, season, cap_limit)
        if space < offer.aav:
            skipped_no_cap += 1
            continue

        # sign new deal
        newc = Contract(
            player_id=pid,
            team_id=offer.team_id,
            start_season=season,
            years=offer.years,
            aav=offer.aav,
            is_rookie=False,
            status="active",
        )
        session.add(newc)
        session.commit()
        compute_and_persist_team_cap(session, offer.team_id, season, cap_limit)
        signed += 1

    return {"signed": signed, "skipped_no_offer": skipped_no_offer, "skipped_no_cap": skipped_no_cap, "skipped_already_signed": skipped_already_signed}
