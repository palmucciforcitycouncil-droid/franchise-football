from typing import Dict, List, Tuple
from math import floor
from sqlmodel import Session, select
from app.models.player_models import Player
from app.models.stats_models import TeamGameStats
from app.models.player_stats_models import PlayerGameStats
from app.engine.rng import RNG

# Usage weights by depth order for MVP (deterministic)
_USAGE = {
    "QB": [1.0],
    "RB": [0.65, 0.25, 0.10],
    "WR": [0.45, 0.35, 0.20, 0.10],
    "TE": [0.70, 0.30],
    "K":  [1.0],
    "P":  [1.0],
}

def _cap_weights(n: int, weights: List[float]) -> List[float]:
    w = weights[:n]
    if len(w) < n:
        # extend with tiny shares if roster thin
        w += [max(0.0, 0.0) for _ in range(n - len(w))]
    s = sum(w) or 1.0
    return [x/s for x in w]

def _players_by_pos(session: Session, team_id: int, pos: str) -> List[Player]:
    rows = session.exec(select(Player).where(Player.team_id==team_id, Player.is_active==True, Player.pos==pos)).all()
    # order by OVR desc (proxy for usage within same depth)
    rows.sort(key=lambda p: p.ovr, reverse=True)
    return rows

def _distribute_int(total: int, shares: List[float]) -> List[int]:
    # integer split that sums exactly to total
    base = [floor(total*s) for s in shares]
    rem = total - sum(base)
    # give remainders to highest shares first
    order = sorted(range(len(shares)), key=lambda i: shares[i], reverse=True)
    for i in range(rem):
        base[order[i % len(base)]] += 1
    return base

def create_player_game_logs_for_team(session: Session, tgs: TeamGameStats, rng: RNG):
    """
    Convert a TeamGameStats row into PlayerGameStats rows for that team.
    Deterministic: seed off game_id+team_id.
    """
    seed = (tgs.game_id * 8191 + tgs.team_id * 131 + tgs.week)
    prng = RNG.with_seed(seed)

    # Fetch active players by position
    qb = _players_by_pos(session, tgs.team_id, "QB")[:1]
    rbs = _players_by_pos(session, tgs.team_id, "RB")[:3]
    wrs = _players_by_pos(session, tgs.team_id, "WR")[:4]
    tes = _players_by_pos(session, tgs.team_id, "TE")[:2]
    k = _players_by_pos(session, tgs.team_id, "K")[:1]
    p = _players_by_pos(session, tgs.team_id, "P")[:1]

    # Synthesize a minimal stat package from team totals
    plays = max(1, tgs.plays)
    yards = max(0, tgs.yards_total)
    pass_y = max(0, tgs.pass_yards)
    rush_y = max(0, tgs.rush_yards)
    points = max(0, tgs.points)

    # Passing: attempts approximate to 0.45–0.60 of plays depending on pass_y share
    pass_att = int(max(10, min(55, 0.5*plays + (pass_y - rush_y) * 0.02)))
    pass_cmp = int(pass_att * (0.58 + 0.06*prng.r().random()))  # 58–64%
    pass_cmp = min(pass_cmp, pass_att)
    pass_td = int(points // 7 * (0.55 + 0.2*prng.r().random()))
    pass_int = int(max(0, min(3, tgs.turnovers - 0)))  # allow team TOs to be mostly INTs for MVP

    # Rushing: carries = plays - dropbacks proxy
    rush_att = max(8, int(plays - pass_att*0.9))
    rush_td = max(0, int((points - pass_td*7) // 7))

    # Receiving: targets = pass_att, receptions = pass_cmp
    rec_tgt = pass_att
    rec_rec = pass_cmp

    # Kick/Punt guesses (very rough; not critical for MVP)
    fg_a = int(max(0, min(5, points // 3 * 0.8)))
    fg_m = int(min(fg_a, fg_a - 1 + int(prng.prob(0.85))))
    xp_a = int(max(0, pass_td + rush_td))
    xp_m = int(min(xp_a, xp_a - int(prng.prob(0.07))))
    punts = int(max(2, min(9, (plays - points) * 0.06)))
    punt_yds = int(punts * (40 + 10*prng.r().random()))

    # Distribute to players by usage weights
    def add_row(pid, pos, **kw):
        session.add(PlayerGameStats(
            season=tgs.season, week=tgs.week, game_id=tgs.game_id,
            team_id=tgs.team_id, player_id=pid, pos=pos, **kw
        ))

    # QB
    if qb:
        add_row(qb[0].id, "QB",
                pass_cmp=pass_cmp, pass_att=pass_att, pass_yds=pass_y,
                pass_td=pass_td, pass_int=pass_int)

    # RB rushing share
    rb_sh = _cap_weights(len(rbs), _USAGE["RB"])
    rb_carries = _distribute_int(rush_att, rb_sh)
    rb_yds = _distribute_int(rush_y, rb_sh)
    rb_tds = _distribute_int(rush_td, rb_sh)
    for i, p in enumerate(rbs):
        add_row(p.id, "RB", rush_att=rb_carries[i], rush_yds=rb_yds[i], rush_td=rb_tds[i])

    # WR/TE receiving split: WR get ~75% of targets/yards, TE ~25%
    wr_share_total = 0.75
    te_share_total = 0.25
    wr_t_sh = _cap_weights(len(wrs), [w*wr_share_total for w in _USAGE["WR"]])
    te_t_sh = _cap_weights(len(tes), [w*te_share_total for w in _USAGE["TE"]])

    wr_tgt = _distribute_int(int(rec_tgt*wr_share_total), wr_t_sh)
    te_tgt = _distribute_int(rec_tgt - sum(wr_tgt), te_t_sh)

    wr_rec = _distribute_int(int(rec_rec*wr_share_total), wr_t_sh)
    te_rec = _distribute_int(rec_rec - sum(wr_rec), te_t_sh)

    wr_yds = _distribute_int(int(pass_y*wr_share_total), wr_t_sh)
    te_yds = _distribute_int(pass_y - sum(wr_yds), te_t_sh)

    # TD split roughly proportional to yards
    wr_td = _distribute_int(max(0, pass_td), [max(0.01, y) for y in wr_yds])
    te_td = _distribute_int(max(0, pass_td - sum(wr_td)), [max(0.01, y) for y in te_yds])

    for i,p in enumerate(wrs):
        add_row(p.id, "WR", rec_tgt=wr_tgt[i], rec_rec=wr_rec[i], rec_yds=wr_yds[i], rec_td=wr_td[i])
    for i,p in enumerate(tes):
        add_row(p.id, "TE", rec_tgt=te_tgt[i], rec_rec=te_rec[i], rec_yds=te_yds[i], rec_td=te_td[i])

    # K/P
    if k:
        add_row(k[0].id, "K", fg_m=fg_m, fg_a=fg_a, xp_m=xp_m, xp_a=xp_a)
    if p:
        add_row(p[0].id, "P", punts=punts, punt_yds=punt_yds)

def persist_player_game_logs_for_game(session: Session, game_id: int):
    # Remove existing rows and rebuild from two TeamGameStats rows
    session.exec(PlayerGameStats.delete().where(PlayerGameStats.game_id==game_id))  # type: ignore[attr-defined]
    tgs = session.exec(select(TeamGameStats).where(TeamGameStats.game_id==game_id)).all()
    if len(tgs) != 2: return
    # Deterministic RNG seeded per team row inside create_player_game_logs_for_team
    for row in tgs:
        create_player_game_logs_for_team(session, row, RNG.with_seed(row.game_id*13 + row.team_id))
    session.commit()

def leaders_for_season(session: Session, season: int) -> Dict[str, List[dict]]:
    rows = session.exec(select(PlayerGameStats).where(PlayerGameStats.season==season)).all()
    agg: Dict[int, dict] = {}
    for r in rows:
        a = agg.setdefault(r.player_id, {"player_id": r.player_id, "team_id": r.team_id, "pos": r.pos,
                                         "pass_yds":0,"pass_td":0,"rush_yds":0,"rush_td":0,"rec_yds":0,"rec_td":0,"fg_m":0,"xp_m":0,"punts":0,"punt_yds":0})
        for k in ["pass_yds","pass_td","rush_yds","rush_td","rec_yds","rec_td","fg_m","xp_m","punts","punt_yds"]:
            a[k] += getattr(r, k)
    # split leaderboards
    def top(key, pos_filter=None, n=10):
        arr = [v for v in agg.values() if (pos_filter is None or v["pos"]==pos_filter)]
        arr.sort(key=lambda x: x.get(key,0), reverse=True)
        return arr[:n]
    return {
        "pass_yds": top("pass_yds", pos_filter="QB"),
        "rush_yds": top("rush_yds", pos_filter="RB"),
        "rec_yds":  top("rec_yds"),
        "rec_td":   top("rec_td"),
        "fg_m":     top("fg_m", pos_filter="K"),
        "xp_m":     top("xp_m", pos_filter="K"),
        "punt_yds": top("punt_yds", pos_filter="P")
    }

