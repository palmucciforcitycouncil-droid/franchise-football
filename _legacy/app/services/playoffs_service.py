from typing import List, Dict, Optional, Tuple
from sqlmodel import Session, select
from app.models.sim_models import SimTeam, SimGame
from app.models.playoffs_models import PlayoffRound, PlayoffMatchup
from app.services.standings_service import head_to_head_record, points_for_against
from app.engine.rng import RNG
from app.engine.game_sim import TeamSim, simulate_game
from app.engine.rating import TeamRatings
from app.services.roster_service import aggregate_team_ratings

ROUND_ORDER = ["WC","DIV","CONF","SB"]

def build_bracket_stub(season_year: int, teams: List) -> dict:
    """Stub function for backward compatibility with existing playoffs API"""
    return {
        "rounds": [],
        "in_the_hunt": []
    }

def _team_sim_from_roster(session: Session, team_id: int):
    t = session.query(SimTeam).filter(SimTeam.id == team_id).first()
    agg = aggregate_team_ratings(session, t.id)
    ratings = TeamRatings(
        offense=agg["offense"], defense=agg["defense"], special=agg["special"],
        run_bias=agg["run_bias"], aggression=agg["aggression"], pace=agg["pace"]
    )
    from app.engine.game_sim import TeamSim
    return TeamSim(name=t.name, abbr=t.abbr, ratings=ratings)

def _standings_sorted(session: Session, season: int, side: str) -> List[int]:
    """Return team ids sorted by W-L, then tiebreakers: head-to-head, PF, PA, power."""
    teams = session.query(SimTeam).filter(SimTeam.conference==side).all()
    # compute records
    wins: Dict[int,int] = {t.id:0 for t in teams}
    losses: Dict[int,int] = {t.id:0 for t in teams}
    games = session.query(SimGame).filter(SimGame.season==season, SimGame.is_played==True).all()
    for g in games:
        if g.home_team_id in wins:
            if g.home_score >= g.away_score: wins[g.home_team_id]+=1
            else: losses[g.home_team_id]+=1
        if g.away_team_id in wins:
            if g.away_score > g.home_score: wins[g.away_team_id]+=1
            else: losses[g.away_team_id]+=1

    def key(team_id: int):
        w = wins[team_id]; l = losses[team_id]
        # tiebreakers computed lazily across comparisons; we approximate by building a tuple
        pf, pa = points_for_against(session, season, team_id)
        power = session.query(SimTeam).filter(SimTeam.id == team_id).first().power
        return (w, -l, pf - pa, pf, power)

    # sort with tie-breaking function using head-to-head if needed
    ids = list(wins.keys())
    ids.sort(key=lambda tid: key(tid), reverse=True)

    # head-to-head pass to adjust local ties
    i = 0
    while i < len(ids)-1:
        a,b = ids[i], ids[i+1]
        if key(a)[:2] == key(b)[:2]:  # same W/L
            ha, hb = head_to_head_record(session, season, a, b)
            if ha != hb and ha < hb:
                ids[i], ids[i+1] = ids[i+1], ids[i]
        i += 1
    return ids

def build_bracket(session: Session, season: int):
    # clear existing bracket for season
    session.query(PlayoffMatchup).filter(PlayoffMatchup.season==season).delete()
    session.query(PlayoffRound).filter(PlayoffRound.season==season).delete()

    for side in ["AFC","NFC"]:
        seeds = _standings_sorted(session, season, side)[:7]
        # Wild Card round
        session.add(PlayoffRound(season=season, round_name="WC", side=side))
        pairs = [(seeds[1], seeds[6]), (seeds[2], seeds[5]), (seeds[3], seeds[4])]  # 2v7, 3v6, 4v5
        for hi, lo in pairs:
            session.add(PlayoffMatchup(season=season, round_name="WC", side=side,
                                       higher_seed_team=hi, lower_seed_team=lo))
        # placeholders for later rounds
        session.add(PlayoffRound(season=season, round_name="DIV", side=side))
        session.add(PlayoffRound(season=season, round_name="CONF", side=side))
    # SB round
    session.add(PlayoffRound(season=season, round_name="SB", side=None))
    session.commit()

def _play_matchup(session: Session, season: int, m: PlayoffMatchup, rng: RNG):
    home_sim = _team_sim_from_roster(session, m.higher_seed_team)
    away_sim = _team_sim_from_roster(session, m.lower_seed_team)
    res = simulate_game(rng, home_sim, away_sim)
    m.higher_seed_score = res.home_score
    m.lower_seed_score = res.away_score
    m.is_complete = True
    m.winner_team_id = m.higher_seed_team if res.home_score >= res.away_score else m.lower_seed_team
    session.add(m)

def _advance_side(session: Session, season: int, side: str, rng: RNG):
    # DIV from WC winners:
    wc = session.query(PlayoffMatchup).filter(
        PlayoffMatchup.season==season, PlayoffMatchup.round_name=="WC", PlayoffMatchup.side==side
    ).all()
    if any(not x.is_complete for x in wc):
        for m in wc: 
            if not m.is_complete: _play_matchup(session, season, m, rng)

    # winners + #1 seed form DIV pairings: #1 vs lowest remaining; other two face
    seeds = _standings_sorted(session, season, side)[:7]
    one_seed = seeds[0]
    winners = [m.winner_team_id for m in wc]
    lo = min(winners, key=lambda tid: seeds.index(tid))
    hi_pair = [x for x in winners if x != lo]
    div_pairs = [(one_seed, lo), (max(hi_pair, key=lambda tid: -seeds.index(tid)), min(hi_pair, key=lambda tid: -seeds.index(tid)))] if len(hi_pair)==2 else []

    for hi, lo in div_pairs:
        session.add(PlayoffMatchup(season=season, round_name="DIV", side=side, higher_seed_team=hi, lower_seed_team=lo))

    session.commit()
    # play DIV
    div = session.query(PlayoffMatchup).filter(
        PlayoffMatchup.season==season, PlayoffMatchup.round_name=="DIV", PlayoffMatchup.side==side
    ).all()
    for m in div:
        if not m.is_complete: _play_matchup(session, season, m, rng)

    # CONF: winners of DIV
    winners = [m.winner_team_id for m in div]
    if len(winners)==2:
        hi, lo = winners[0], winners[1]
        # order by seed index (lower index is higher seed)
        seeds_idx = {tid:i for i,tid in enumerate(seeds)}
        if seeds_idx[lo] < seeds_idx[hi]: hi, lo = lo, hi
        session.add(PlayoffMatchup(season=season, round_name="CONF", side=side, higher_seed_team=hi, lower_seed_team=lo))
        session.commit()
        conf = session.query(PlayoffMatchup).filter(
            PlayoffMatchup.season==season, PlayoffMatchup.round_name=="CONF", PlayoffMatchup.side==side
        ).first()
        if conf and not conf.is_complete: _play_matchup(session, season, conf, rng)
    session.commit()

def run_playoffs(session: Session, season: int, seed: int):
    rng = RNG.with_seed(seed * 7919 + season)
    # build if missing
    if not session.query(PlayoffRound).filter(PlayoffRound.season==season).first():
        build_bracket(session, season)
    # advance AFC & NFC to CONF winners
    for side in ["AFC","NFC"]:
        _advance_side(session, season, side, rng)
    # build & play SB
    afc_champ = session.query(PlayoffMatchup).filter(
        PlayoffMatchup.season==season, PlayoffMatchup.round_name=="CONF", PlayoffMatchup.side=="AFC"
    ).first()
    nfc_champ = session.query(PlayoffMatchup).filter(
        PlayoffMatchup.season==season, PlayoffMatchup.round_name=="CONF", PlayoffMatchup.side=="NFC"
    ).first()
    if afc_champ and nfc_champ and afc_champ.is_complete and nfc_champ.is_complete:
        sb_existing = session.query(PlayoffMatchup).filter(
            PlayoffMatchup.season==season, PlayoffMatchup.round_name=="SB"
        ).first()
        if not sb_existing:
            session.add(PlayoffMatchup(
                season=season, round_name="SB", side=None,
                higher_seed_team=afc_champ.winner_team_id, lower_seed_team=nfc_champ.winner_team_id
            ))
            session.commit()
        sb = session.query(PlayoffMatchup).filter(
            PlayoffMatchup.season==season, PlayoffMatchup.round_name=="SB"
        ).first()
        if sb and not sb.is_complete:
            _play_matchup(session, season, sb, rng)
    session.commit()

def get_bracket_dto(session: Session, season: int) -> dict:
    """Return data in the Figma DTO shape used by the Playoffs UI."""
    def team_info(tid: int):
        t = session.query(SimTeam).filter(SimTeam.id == tid).first()
        return {
            "team_id": tid, "team_name": t.name, "team_abbr": t.abbr,
            "seed": 0, "logo_url": None, "conference": t.conference
        }
    rounds = []
    for rn in ROUND_ORDER:
        if rn == "SB":
            mm = session.query(PlayoffMatchup).filter(PlayoffMatchup.season==season, PlayoffMatchup.round_name==rn).all()
            rounds.append({
                "round_id": rn, "round_name": rn, "matchups": [
                    {
                        "matchup_id": f"{rn}-{m.id}",
                        "round": rn,
                        "side": None,
                        "higher_seed_team": team_info(m.higher_seed_team),
                        "lower_seed_team": team_info(m.lower_seed_team),
                        "higher_seed_score": m.higher_seed_score,
                        "lower_seed_score": m.lower_seed_score,
                        "is_complete": m.is_complete,
                        "winner_team_id": m.winner_team_id
                    } for m in mm
                ]
            })
        else:
            for side in ["AFC","NFC"]:
                mm = session.query(PlayoffMatchup).filter(
                    PlayoffMatchup.season==season, PlayoffMatchup.round_name==rn, PlayoffMatchup.side==side
                ).all()
                rounds.append({
                    "round_id": f"{rn}-{side}", "round_name": rn, "matchups": [
                        {
                            "matchup_id": f"{rn}-{m.id}",
                            "round": rn, "side": side,
                            "higher_seed_team": team_info(m.higher_seed_team),
                            "lower_seed_team": team_info(m.lower_seed_team),
                            "higher_seed_score": m.higher_seed_score,
                            "lower_seed_score": m.lower_seed_score,
                            "is_complete": m.is_complete,
                            "winner_team_id": m.winner_team_id
                        } for m in mm
                    ]
                })
    # simple "in the hunt": next 3 per conference outside top 7
    def hunt(side: str):
        order = _standings_sorted(session, season, side)
        return [
            {
                "team_id": tid,
                "team_name": session.query(SimTeam).filter(SimTeam.id == tid).first().name,
                "team_abbr": session.query(SimTeam).filter(SimTeam.id == tid).first().abbr,
                "side": side, "games_back": 0.5*(i-6) if i>6 else 0.0,
                "seed_if_made": min(i+1, 7), "current_record": "-"
            } for i, tid in enumerate(order[7:10], start=8)
        ]
    in_the_hunt = hunt("AFC") + hunt("NFC")
    return {"rounds": rounds, "in_the_hunt": in_the_hunt}