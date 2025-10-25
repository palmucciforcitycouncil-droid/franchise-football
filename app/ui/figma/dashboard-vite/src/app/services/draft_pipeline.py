# app/services/draft_pipeline.py
from __future__ import annotations
from typing import Dict, Any, List, Tuple
import random
from sqlmodel import Session, select, delete
from app.models.draft import Prospect
from app.models.core_min import Player
from app.services.draft_compare import board_score  # reuse weights for OVR calc target
from app.services.draft_integration import _ensure_player_fields, _to_player_attrs_from_prospect  # reuse mapper
from app.models.contracts import Contract
from app.services.contracts import list_free_agents  # for sanity checks
from app.models.draft_audit import ProspectProgressAudit

RATING_MIN, RATING_MAX = 30, 99

# --- Position distribution for ~300 prospects per class ---
POSITION_COUNTS = {
    "QB": 15, "RB": 26, "WR": 39, "TE": 16, "OL": 48,
    "DL": 51, "LB": 42, "DB": 61, "K": 3, "P": 3,
}
CLASS_SIZE = sum(POSITION_COUNTS.values())  # 304

def _clamp(v:int, lo:int=RATING_MIN, hi:int=RATING_MAX) -> int:
    return max(lo, min(hi, v))

def _rng_for(master_seed:int, season:int, pid:int) -> random.Random:
    return random.Random(master_seed ^ season ^ pid)

def _ovr_from_attrs(pos:str, attrs:dict) -> int:
    """
    Recompute OVR using the same positional notion as board_score,
    then normalize into 30..99 (soft cap mid-80s; rare outliers).
    """
    # derive pseudo-score with same feature set as board_score
    fake = type("Tmp", (), {})()
    for k,v in attrs.items(): setattr(fake, k, v)
    setattr(fake, "pos", pos)
    score = board_score(fake)  # typically ~50..90
    # Map score (roughly 40..95) to OVR 30..99 with a soft cap ~86 (occasional 87-89 outliers)
    raw = int(round(score))
    soft_capped = min(raw, 86)
    # tiny rare boost: 0.5% can reach 87-89 if raw>86
    if raw > 86:
        soft_capped = min(89, 86 + min(3, raw - 86))
    return _clamp(soft_capped)

def _biased_jitter(rng: random.Random, base:int, lo:int, hi:int, mean_bias:int) -> int:
    """
    Jitter in [base+(-hi..+hi)] but center shifted upward by mean_bias (positive trajectory).
    Implemented as base + mean_bias + uniform(-hi..hi), then clamped.
    """
    delta = mean_bias + rng.randint(-hi, hi)
    return _clamp(base + delta)

def _age_seed_start(rng: random.Random) -> int:
    # FR start age 18 or 19 (roughly even)
    return 18 if rng.random() < 0.55 else 19

# --- Generation helpers (reuse your existing archetype logic) ---
def _gen_attr(rng: random.Random, base:int, spread:int) -> int:
    return _clamp(base + rng.randint(-spread, spread))

POS_BASES = {
    # baseline component means for FR (~lower than pro means)
    # These are intentionally modest so FR OVR ≈ 50 ± 6 overall
    "QB":  {"ath": 60, "aware": 55, "overall": 50},
    "RB":  {"ath": 62, "aware": 50, "overall": 50},
    "WR":  {"ath": 62, "aware": 50, "overall": 50},
    "TE":  {"ath": 60, "aware": 52, "overall": 50},
    "OL":  {"ath": 58, "aware": 55, "overall": 50},
    "DL":  {"ath": 60, "aware": 50, "overall": 50},
    "LB":  {"ath": 60, "aware": 52, "overall": 50},
    "DB":  {"ath": 62, "aware": 52, "overall": 50},
    "K":   {"ath": 50, "aware": 56, "overall": 50},
    "P":   {"ath": 50, "aware": 56, "overall": 50},
}

def _generate_single_prospect(rng: random.Random, name:str, pos:str, class_year:str, expected_draft_season:int, master_seed:int, pid_hint:int) -> Prospect:
    b = POS_BASES[pos]
    speed     = _gen_attr(rng, b["ath"], 8)
    agility   = _gen_attr(rng, b["ath"], 8)
    strength  = _gen_attr(rng, 60 if pos in {"OL","DL","TE","LB"} else 55, 8)
    awareness = _gen_attr(rng, b["aware"], 6)
    potential = _gen_attr(rng, 74, 14)
    # derive stamina & morale consistent with your player model bounds (optional)
    attrs = dict(speed=speed, agility=agility, strength=strength, awareness=awareness, potential=potential)
    ovr = _ovr_from_attrs(pos, attrs)
    # Freeze age
    age = _age_seed_start(rng) if class_year == "FR" else (19 if class_year=="SO" else 20 if class_year=="JR" else 21)
    return Prospect(
        season=expected_draft_season,  # keep backward compatibility; season==expected_draft_season
        name=name, pos=pos,
        overall=ovr, speed=speed, strength=strength, agility=agility, awareness=awareness, potential=potential,
        class_year=class_year, expected_draft_season=expected_draft_season, eligible_season=None,
        drafted_by_team_id=None, drafted_overall_pick=None, age=age, watchlist=False
    )

# --- Name gen placeholder (use your existing if available) ---
def _name_gen(rng: random.Random, pos: str, idx: int) -> str:
    firsts = ["Jayden","Caleb","Mason","Noah","Aiden","Ethan","Liam","Logan","Kai","Leo","Micah","Owen","Miles","Avery","Jace"]
    lasts  = ["Walker","Johnson","Smith","Bennett","Campbell","Murphy","Lewis","Hall","Rivera","Stewart","Carter","Reed","Torres","Gray","Sims"]
    return f"{rng.choice(firsts)} {rng.choice(lasts)}-{pos}{idx}"

# --- Public API ---

def seed_four_year_pipeline(session: Session, current_season: int, master_seed: int = 2025) -> Dict[str, Any]:
    """
    Create SR (current_season), JR (current_season+1), SO (+2), FR (+3) classes.
    Idempotent: If any class already exists (by expected_draft_season), we skip creation for that season.
    """
    created = 0
    horizon = {
        "SR": current_season,
        "JR": current_season + 1,
        "SO": current_season + 2,
        "FR": current_season + 3,
    }
    # if any prospects already exist for expected_draft_season, assume class is seeded
    for cy, es in horizon.items():
        exists = session.exec(select(Prospect).where(Prospect.expected_draft_season==es)).first()
        if exists:
            continue
        rng = random.Random(master_seed ^ es)
        idx = 1
        for pos, count in POSITION_COUNTS.items():
            for _ in range(count):
                name = _name_gen(rng, pos, idx); idx += 1
                p = _generate_single_prospect(rng, name, pos, class_year=cy, expected_draft_season=es, master_seed=master_seed, pid_hint=idx)
                session.add(p)
        session.commit()
        created += CLASS_SIZE
    return {"created": created, "classes": horizon}

def _apply_yearly_dev(rng: random.Random, pos:str, class_year_from:str, attrs:dict) -> dict:
    """
    Apply positive-trajectory jitter to core attributes.
    FR->SO: ±10, +6 mean
    SO->JR: ±5,  +3 mean
    JR->SR: ±3,  +1 mean
    """
    bands = {"FR": (10, 6), "SO": (5, 3), "JR": (3, 1)}
    hi, bias = bands[class_year_from]
    out = {}
    for k in ("speed","agility","strength","awareness","potential"):
        out[k] = _biased_jitter(rng, attrs[k], lo=0, hi=hi, mean_bias=bias)
    return out

def _maybe_early_declare(rng: random.Random, pos:str, ovr:int) -> bool:
    """
    Early-declare probabilities tuned to your spec:
    - No 90+ drafts generally; best usually low-mid 80s.
    - QBs: >=70 are 'likely' to declare early.
    We'll implement smooth ramps:
      QB: 70..85 → 30%..70% (linear)
      RB/WR/TE/DB/LB/DL: 75..85 → 20%..60%
      OL: 78..86 → 15%..45%
      K/P: 82..88 → 10%..30%
    """
    pos = pos.upper()
    def lerp(x,a0,a1,b0,b1):
        if x<=a0: return b0
        if x>=a1: return b1
        return b0 + (b1-b0)*((x-a0)/(a1-a0))
    if pos=="QB":
        p = lerp(ovr, 70, 85, 0.30, 0.70)
    elif pos in {"RB","WR","TE","DB","LB","DL"}:
        p = lerp(ovr, 75, 85, 0.20, 0.60)
    elif pos=="OL":
        p = lerp(ovr, 78, 86, 0.15, 0.45)
    else:  # K/P
        p = lerp(ovr, 82, 88, 0.10, 0.30)
    return rng.random() < max(0.0, min(0.95, p))

def rollover_draft_pipeline(session: Session, next_season: int, master_seed:int=2025, max_early_declares:int=25) -> Dict[str, Any]:
    """
    Advance classes and apply development into the upcoming season `next_season`.
    - Generate a NEW FR class for next_season+3 (if not present)
    - Advance FR->SO, SO->JR, JR->SR w/ biased jitter and recompute OVR
    - Set eligible_season for SR and early declarers (JR/SO rare)
    - Early declarations capped at max_early_declares
    Idempotent per season (guard: if any prospect already has expected_draft_season==next_season+3 and class_year=='FR', we assume this rollover already ran).
    """
    # guard idempotency by checking if next FR exists
    fr_exists = session.exec(select(Prospect).where(Prospect.expected_draft_season==next_season+3, Prospect.class_year=="FR")).first()
    if fr_exists:
        return {"status":"noop"}
    # 1) generate new FR class for (next_season+3)
    seed_four_year_pipeline(session, next_season, master_seed)  # this will only create missing classes

    early_declared = 0
    promoted_counts = {"FR->SO":0,"SO->JR":0,"JR->SR":0,"JR->DECL":0,"SO->DECL":0}

    # 2) advance existing (those whose expected_draft_season in {next_season, next+1, next+2})
    rows = session.exec(select(Prospect)).all()
    for p in rows:
        # Capture BEFORE snapshot for audit
        before_ovr = int(p.overall or 0)
        before_year = p.class_year

        # Skip players that already became eligible in a past season
        # We only advance those on the pipeline forward to their target draft season
        if p.class_year == "SR" and (p.eligible_season == p.expected_draft_season):
            # SR will be handled by finalize_draft_year separately
            continue

        rng = _rng_for(master_seed, next_season, p.id or 0)

        if p.class_year == "FR" and p.expected_draft_season == next_season+3:
            # Newly created FR this call; already initialized
            continue

        # Advance by one year where applicable
        if p.class_year == "FR":
            # dev
            updates = _apply_yearly_dev(rng, p.pos, "FR", dict(speed=p.speed, agility=p.agility, strength=p.strength, awareness=p.awareness, potential=p.potential))
            p.speed, p.agility, p.strength, p.awareness, p.potential = updates["speed"],updates["agility"],updates["strength"],updates["awareness"],updates["potential"]
            p.age += 1
            p.class_year = "SO"
            promoted_counts["FR->SO"] += 1

        elif p.class_year == "SO":
            updates = _apply_yearly_dev(rng, p.pos, "SO", dict(speed=p.speed, agility=p.agility, strength=p.strength, awareness=p.awareness, potential=p.potential))
            p.speed, p.agility, p.strength, p.awareness, p.potential = updates["speed"],updates["agility"],updates["strength"],updates["awareness"],updates["potential"]
            p.age += 1
            # Rare SO early declare if OVR gets very high; keep cap small via main cap
            will_decl = False
            if early_declared < max_early_declares:
                ovr_tmp = _ovr_from_attrs(p.pos, {"speed":p.speed,"agility":p.agility,"strength":p.strength,"awareness":p.awareness,"potential":p.potential})
                if ovr_tmp >= 85 and _maybe_early_declare(rng, p.pos, ovr_tmp):  # very rare SO
                    will_decl = True
            if will_decl and early_declared < max_early_declares:
                p.eligible_season = next_season
                p.class_year = "SR"  # becomes eligible now
                early_declared += 1
                promoted_counts["SO->DECL"] += 1
            else:
                p.class_year = "JR"
                promoted_counts["SO->JR"] += 1

        elif p.class_year == "JR":
            updates = _apply_yearly_dev(rng, p.pos, "JR", dict(speed=p.speed, agility=p.agility, strength=p.strength, awareness=p.awareness, potential=p.potential))
            p.speed, p.agility, p.strength, p.awareness, p.potential = updates["speed"],updates["agility"],updates["strength"],updates["awareness"],updates["potential"]
            p.age += 1
            # JR early declare (main path)
            will_decl = False
            if early_declared < max_early_declares:
                ovr_tmp = _ovr_from_attrs(p.pos, {"speed":p.speed,"agility":p.agility,"strength":p.strength,"awareness":p.awareness,"potential":p.potential})
                # QB likely at >=70, others need ~75+
                thresh = 70 if p.pos.upper()=="QB" else 75
                if ovr_tmp >= thresh and _maybe_early_declare(rng, p.pos, ovr_tmp):
                    will_decl = True
            if will_decl and early_declared < max_early_declares:
                p.eligible_season = next_season
                p.class_year = "SR"
                early_declared += 1
                promoted_counts["JR->DECL"] += 1
            else:
                p.class_year = "SR"
                p.eligible_season = p.expected_draft_season if p.expected_draft_season == next_season else next_season  # ensure SR eligible this season if they reached SR
                promoted_counts["JR->SR"] += 1

        elif p.class_year == "SR":
            # Seniors should be eligible this season (next_season) if they weren't already marked
            if p.eligible_season is None:
                p.eligible_season = next_season

        # Recompute OVR after any updates
        p.overall = _ovr_from_attrs(p.pos, {"speed":p.speed,"agility":p.agility,"strength":p.strength,"awareness":p.awareness,"potential":p.potential})
        session.add(p)

        # Write idempotent audit row (one per season+prospect)
        existing_audit = session.exec(
            select(ProspectProgressAudit).where(
                ProspectProgressAudit.season == next_season,
                ProspectProgressAudit.prospect_id == (p.id or 0),
            )
        ).first()
        if not existing_audit:
            session.add(ProspectProgressAudit(
                season=next_season,
                prospect_id=p.id or 0,
                pos=p.pos,
                class_year=p.class_year,
                age=p.age,
                ovr_before=before_ovr,
                ovr_after=int(p.overall or 0),
            ))

    session.commit()
    return {"status":"ok","early_declared":early_declared,"promoted":promoted_counts}

def finalize_draft_year(session: Session, season:int) -> Dict[str, Any]:
    """
    After the draft completes:
    - Any eligible prospect for `season` without drafted_by_team_id becomes a UDFA Player (team_id=None).
    - Remove prospect rows after promotion.
    - At season end, a cleanup can prune UDFAs with no contracts.
    """
    promoted = 0
    removed = 0
    # Eligible pool = SRs / declarers with eligible_season==season
    pool = session.exec(select(Prospect).where(Prospect.eligible_season==season)).all()
    for pr in pool:
        if pr.drafted_by_team_id:
            # drafted prospects will be handled by your existing promotion (finalize picks)
            continue
        # promote to Player as UDFA
        pl = Player()
        if hasattr(pl,"name"): setattr(pl,"name", pr.name)
        attrs = {
            "speed": pr.speed, "agility": pr.agility, "strength": pr.strength,
            "awareness": pr.awareness, "potential": pr.potential,
            "throw_power": 50, "throw_accuracy": 50, "catching": 50, "tackling": 50,
        }
        mapped = _to_player_attrs_from_prospect(pr.pos, pr, jitter=0, rng=None)
        _ensure_player_fields(pl, mapped)
        if hasattr(pl,"position"): pl.position = pr.pos
        elif hasattr(pl,"pos"): pl.pos = pr.pos
        if hasattr(pl,"team_id"): pl.team_id = None
        if hasattr(pl,"age"): pl.age = pr.age + 0  # keep
        if hasattr(pl,"potential"): pl.potential = pr.potential
        if hasattr(pl,"is_rookie"): pl.is_rookie = True
        if hasattr(pl,"rookie_season"): pl.rookie_season = season
        if hasattr(pl,"prospect_id"): pl.prospect_id = pr.id
        session.add(pl); session.flush()
        promoted += 1
        # remove prospect row (Option A keeps rows, but for graduates we delete to avoid reprocessing)
        session.delete(pr); removed += 1
    session.commit()
    return {"udfa_promoted": promoted, "prospects_deleted": removed}
