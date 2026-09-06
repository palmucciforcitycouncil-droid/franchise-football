from __future__ import annotations
from typing import List, Dict, Any, Tuple
from fastapi import APIRouter, HTTPException
from sqlmodel import select
import json, random, math

from app.core.db import session_scope
from app.models.sim_models import Team, Game, GameEvent

router = APIRouter(prefix="/api/sim", tags=["sim"])

NFL_TEAMS: List[Dict[str, str]] = [
    {"abbr":"BUF","city":"Buffalo","name":"Bills","conference":"AFC","division":"East"},
    {"abbr":"MIA","city":"Miami","name":"Dolphins","conference":"AFC","division":"East"},
    {"abbr":"NE","city":"New England","name":"Patriots","conference":"AFC","division":"East"},
    {"abbr":"NYJ","city":"New York","name":"Jets","conference":"AFC","division":"East"},
    {"abbr":"BAL","city":"Baltimore","name":"Ravens","conference":"AFC","division":"North"},
    {"abbr":"CIN","city":"Cincinnati","name":"Bengals","conference":"AFC","division":"North"},
    {"abbr":"CLE","city":"Cleveland","name":"Browns","conference":"AFC","division":"North"},
    {"abbr":"PIT","city":"Pittsburgh","name":"Steelers","conference":"AFC","division":"North"},
    {"abbr":"HOU","city":"Houston","name":"Texans","conference":"AFC","division":"South"},
    {"abbr":"IND","city":"Indianapolis","name":"Colts","conference":"AFC","division":"South"},
    {"abbr":"JAX","city":"Jacksonville","name":"Jaguars","conference":"AFC","division":"South"},
    {"abbr":"TEN","city":"Tennessee","name":"Titans","conference":"AFC","division":"South"},
    {"abbr":"DEN","city":"Denver","name":"Broncos","conference":"AFC","division":"West"},
    {"abbr":"KC","city":"Kansas City","name":"Chiefs","conference":"AFC","division":"West"},
    {"abbr":"LV","city":"Las Vegas","name":"Raiders","conference":"AFC","division":"West"},
    {"abbr":"LAC","city":"Los Angeles","name":"Chargers","conference":"AFC","division":"West"},
    {"abbr":"DAL","city":"Dallas","name":"Cowboys","conference":"NFC","division":"East"},
    {"abbr":"NYG","city":"New York","name":"Giants","conference":"NFC","division":"East"},
    {"abbr":"PHI","city":"Philadelphia","name":"Eagles","conference":"NFC","division":"East"},
    {"abbr":"WAS","city":"Washington","name":"Commanders","conference":"NFC","division":"East"},
    {"abbr":"CHI","city":"Chicago","name":"Bears","conference":"NFC","division":"North"},
    {"abbr":"DET","city":"Detroit","name":"Lions","conference":"NFC","division":"North"},
    {"abbr":"GB","city":"Green Bay","name":"Packers","conference":"NFC","division":"North"},
    {"abbr":"MIN","city":"Minnesota","name":"Vikings","conference":"NFC","division":"North"},
    {"abbr":"ATL","city":"Atlanta","name":"Falcons","conference":"NFC","division":"South"},
    {"abbr":"CAR","city":"Carolina","name":"Panthers","conference":"NFC","division":"South"},
    {"abbr":"NO","city":"New Orleans","name":"Saints","conference":"NFC","division":"South"},
    {"abbr":"TB","city":"Tampa Bay","name":"Buccaneers","conference":"NFC","division":"South"},
    {"abbr":"ARI","city":"Arizona","name":"Cardinals","conference":"NFC","division":"West"},
    {"abbr":"LAR","city":"Los Angeles","name":"Rams","conference":"NFC","division":"West"},
    {"abbr":"SEA","city":"Seattle","name":"Seahawks","conference":"NFC","division":"West"},
    {"abbr":"SF","city":"San Francisco","name":"49ers","conference":"NFC","division":"West"},
]

RATING: Dict[str, float] = {
    "KC": 3.0, "SF": 2.6, "BAL": 2.4, "BUF": 2.0, "DET": 1.6, "DAL": 1.5, "PHI": 1.2, "CIN": 1.0,
    "MIA": 0.9, "HOU": 0.8, "GB": 0.6, "LAR": 0.4, "JAX": 0.2, "CLE": 0.1, "SEA": 0.0, "PIT": 0.0,
    "MIN": -0.2, "NO": -0.3, "TB": -0.4, "IND": -0.5, "NYJ": -0.6, "CHI": -0.7, "DEN": -0.8, "LAC": -0.9,
    "LV": -1.0, "ATL": -1.1, "WAS": -1.3, "CAR": -1.6, "TEN": -1.7, "NYG": -1.8, "NE": -2.0, "ARI": -2.2,
}

def _rng(home_id:int, away_id:int, season:int, week:int) -> random.Random:
    seed = (home_id * 73856093) ^ (away_id * 19349663) ^ (season * 83492791) ^ (week * 2654435761)
    return random.Random(seed & 0x7FFFFFFF)

def _team_by_id_map(s) -> Dict[int, Team]:
    return {t.id: t for t in s.exec(select(Team)).all()}

def _round_robin_round(team_ids: List[int], round_index: int) -> List[Tuple[int,int]]:
    n = len(team_ids)
    fixed = team_ids[0]
    rot = team_ids[1:].copy()
    k = round_index % (n - 1)
    rot = rot[k:] + rot[:k]
    order = [fixed] + rot
    pairs: List[Tuple[int,int]] = []
    for i in range(n // 2):
        a = order[i]
        b = order[n - 1 - i]
        pairs.append((a, b))
    return pairs

def _assign_byes(team_ids: List[int], season:int) -> Dict[int, int]:
    byes: Dict[int,int] = {}
    for tid in team_ids:
        w = 6 + ((tid * 97 + season * 13) % 9)  # 6..14
        byes[tid] = w
    return byes

def _place_rounds_into_18_weeks(team_ids: List[int], season:int, rounds: List[List[Tuple[int,int]]]) -> Dict[int, List[Tuple[int,int]]]:
    byes = _assign_byes(team_ids, season)
    weeks: Dict[int, List[Tuple[int,int]]] = {w: [] for w in range(1, 19)}
    team_week_busy: Dict[Tuple[int,int], bool] = {}
    for r_pairs in rounds:
        placed = False
        for wk in range(1, 19):
            if any(byes[a] == wk or byes[b] == wk for (a,b) in r_pairs): continue
            if any(team_week_busy.get((a, wk)) or team_week_busy.get((b, wk)) for (a,b) in r_pairs): continue
            if len(weeks[wk]) + len(r_pairs) > 16: continue
            weeks[wk].extend(r_pairs)
            for (a,b) in r_pairs:
                team_week_busy[(a, wk)] = True
                team_week_busy[(b, wk)] = True
            placed = True
            break
        if not placed:
            for wk in range(1, 19):
                for (a,b) in r_pairs:
                    if byes[a] == wk or byes[b] == wk: continue
                    if team_week_busy.get((a, wk)) or team_week_busy.get((b, wk)): continue
                    if len(weeks[wk]) < 16:
                        weeks[wk].append((a,b))
                        team_week_busy[(a, wk)] = True
                        team_week_busy[(b, wk)] = True
    return weeks

def _expected_points_and_margin(home_abbr:str, away_abbr:str) -> Tuple[float,float]:
    base_total = 43.5
    hfa = 2.0
    h_rating = RATING.get(home_abbr, 0.0)
    a_rating = RATING.get(away_abbr, 0.0)
    rating_diff = h_rating - a_rating
    total = base_total + 0.35 * abs(rating_diff)
    margin = hfa + 0.9 * rating_diff
    return total, margin

def _discrete_score_sim(r:random.Random, exp_total:float, exp_margin:float) -> Tuple[int,int, list]:
    avg_pts_per = 3.9
    total_chances = max(10, min(18, int(round(exp_total / avg_pts_per))))
    bias = max(-3, min(3, int(round(exp_margin / 2.2))))
    home_chances = (total_chances // 2) + max(0, bias)
    away_chances = total_chances - home_chances
    def take_points(n:int) -> Tuple[int,list]:
        pts = 0; ev=[]
        for _ in range(n):
            x = r.random()
            if x < 0.56:      # TD
                pts += 7; ev.append(("td",7))
            elif x < 0.89:    # FG
                pts += 3; ev.append(("fg",3))
            elif x < 0.93:    # Safety
                pts += 2; ev.append(("safety",2))
        return pts, ev
    hp, hev = take_points(home_chances)
    ap, aev = take_points(away_chances)
    if hp == ap:
        if r.random() < 0.55: hp += 3
        else: ap += 3
    else:
        if r.random() < 0.30:
            diff = hp - ap
            if diff > 0 and diff % 3 == 1: hp += 2
            elif diff < 0 and (-diff) % 3 == 1: ap += 2
    return hp, ap, hev + aev

def _simulate_pbp_for_game(s, g:Game, season:int, week:int, hs:int, as_:int, h_abbr:str, a_abbr:str) -> None:
    r = _rng(g.home_team_id, g.away_team_id, season, week)
    q, clock = 1, 900
    sh, sa = 0, 0
    def emit(etype:str, data:Dict[str,Any]):
        nonlocal q, clock, sh, sa
        s.add(GameEvent(
            game_id=g.id, quarter=q, clock=f"{clock//60:02d}:{clock%60:02d}",
            event_type=etype, description=json.dumps(data, separators=(",",":")),
            score_home=sh, score_away=sa
        ))
    sequences = r.randint(20, 26)
    for d in range(sequences):
        offense = "home" if d % 2 == 0 else "away"
        snaps = r.randint(3, 7)
        for _ in range(snaps):
            play = "pass" if r.random() < 0.56 else "run"
            yards = r.randint(-4, 18) if play == "run" else r.randint(-6, 28)
            first = yards >= 10
            emit("play", {"team":offense,"play":play,"yards":yards,"first_down":first})
            clock = max(0, clock - r.randint(12, 38))
            if clock == 0:
                q = min(4, q + 1)
                clock = 900
                if q == 4 and r.random() < 0.15:
                    break
        x = r.random()
        if x < 0.12:
            emit("turnover", {"team":offense})
        elif x < 0.50:
            if offense == "home": sh += 3
            else: sa += 3
            emit("fg", {"team":offense,"good":True})
        else:
            if offense == "home": sh += 7
            else: sa += 7
            emit("td", {"team":offense,"type":"rush" if r.random()<0.45 else "pass"})
    sh, sa = hs, as_
    emit("final", {"home":h_abbr,"away":a_abbr})

@router.post("/seed-teams")
def seed_teams() -> dict:
    with session_scope() as s:
        existing = s.exec(select(Team)).all()
        if existing:
            return {"ok": True, "message": "Teams already seeded", "count": len(existing)}
        for t in NFL_TEAMS:
            s.add(Team(**t))
        s.commit()
        total = len(s.exec(select(Team)).all())
        return {"ok": True, "message": "Seeded teams", "count": total}

@router.post("/schedule/{season}")
def build_schedule_week1(season: int) -> dict:
    with session_scope() as s:
        teams = s.exec(select(Team).order_by(Team.id)).all()
        if len(teams) != 32:
            raise HTTPException(status_code=400, detail="Seed teams first (need 32).")
        if s.exec(select(Game).where(Game.season==season, Game.week==1)).first():
            return {"ok": True, "message": "Schedule already exists for Week 1", "games": 16}
        for i in range(0, 32, 2):
            away = teams[i]; home = teams[i+1]
            s.add(Game(season=season, week=1, home_team_id=home.id, away_team_id=away.id, status="scheduled"))
        s.commit()
        return {"ok": True, "message": "Built Week 1 schedule", "games": 16}

@router.post("/schedule-all/{season}")
def build_full_schedule(season: int) -> dict:
    with session_scope() as s:
        teams = s.exec(select(Team).order_by(Team.id)).all()
        if len(teams) != 32:
            raise HTTPException(status_code=400, detail="Seed teams first (need 32).")
        team_ids = [t.id for t in teams]
        rounds = [_round_robin_round(team_ids, r) for r in range(17)]
        weeks_plan = _place_rounds_into_18_weeks(team_ids, season, rounds)
        created = 0
        for wk in range(1, 19):
            existing = s.exec(select(Game).where(Game.season == season, Game.week == wk)).all()
            have_pairs = {(g.home_team_id, g.away_team_id) for g in existing} | {(g.away_team_id, g.home_team_id) for g in existing}
            to_add: List[Tuple[int,int]] = []
            for (a,b) in weeks_plan[wk]:
                if (a,b) in have_pairs or (b,a) in have_pairs: continue
                idx = len(existing) + len(to_add)
                home, away = (b, a) if ((wk + idx) % 2 == 0) else (a, b)
                to_add.append((home, away))
            for (home, away) in to_add:
                s.add(Game(season=season, week=wk, home_team_id=home, away_team_id=away, status="scheduled"))
                created += 1
        s.commit()
        return {"ok": True, "message": "Upserted 17 game, 18 week schedule", "games_created": created}

@router.post("/play-week/{season}/{week}")
def play_week(season: int, week: int) -> dict:
    with session_scope() as s:
        games = s.exec(select(Game).where(Game.season == season, Game.week == week)).all()
        if not games:
            raise HTTPException(status_code=400, detail="No scheduled games for given season/week.")
        teams = _team_by_id_map(s)
        for g in games:
            if g.status == "final": continue
            h = teams[g.home_team_id].abbr; a = teams[g.away_team_id].abbr
            exp_total, exp_margin = _expected_points_and_margin(h, a)
            r = _rng(g.home_team_id, g.away_team_id, season, week)
            ht, hp, at, ap = _yardage_targets(r, rating_diff=(RATING.get(h,0.0)-RATING.get(a,0.0)))
            pts_h, pts_a = _points_from_yards(r, ht, at, exp_margin)
            hs, as_, evs = _discrete_score_sim(r, exp_total, exp_margin, pts_h, pts_a)
            _simulate_pbp_for_game(s, g, season, week, hs, as_, h, a, ht, hp, at, ap, evs)
            g.home_score, g.away_score, g.status = hs, as_, "final"
        s.commit()
        return {"ok": True, "message": f"Played week {week}", "games": len(games)}

@router.post("/play-season/{season}")
def play_season(season: int) -> dict:
    with session_scope() as s:
        teams = _team_by_id_map(s)
        total = 0
        for wk in range(1, 19):
            games = s.exec(select(Game).where(Game.season == season, Game.week == wk)).all()
            for g in games:
                if g.status == "final": continue
                h = teams[g.home_team_id].abbr; a = teams[g.away_team_id].abbr
                exp_total, exp_margin = _expected_points_and_margin(h, a)
                r = _rng(g.home_team_id, g.away_team_id, season, wk)
                ht, hp, at, ap = _yardage_targets(r, rating_diff=(RATING.get(h,0.0)-RATING.get(a,0.0)))
            pts_h, pts_a = _points_from_yards(r, ht, at, exp_margin)
            hs, as_, evs = _discrete_score_sim(r, exp_total, exp_margin, pts_h, pts_a)
                _simulate_pbp_for_game_v2(s, g, season, wk, hs, as_, h, a, ht, hp, at, ap, evs)
                g.home_score, g.away_score, g.status = hs, as_, "final"
                total += 1
        s.commit()
        return {"ok": True, "message": "Season played weeks 1-18", "games_finalized": total}

@router.get("/games/{season}/{week}")
def get_games(season: int, week: int) -> dict:
    with session_scope() as s:
        rows = s.exec(select(Game).where(Game.season == season, Game.week == week)).all()
        return {"ok": True, "games": [
            {"id": g.id, "season": g.season, "week": g.week,
             "home_team_id": g.home_team_id, "away_team_id": g.away_team_id,
             "home_score": g.home_score, "away_score": g.away_score, "status": g.status}
            for g in rows
        ]}

@router.get("/pbp/{season}/{week}")
def get_pbp(season:int, week:int) -> dict:
    with session_scope() as s:
        games = s.exec(select(Game).where(Game.season==season, Game.week==week)).all()
        out = []
        for g in games:
            evs = s.exec(select(GameEvent).where(GameEvent.game_id==g.id).order_by(GameEvent.id)).all()
            out.append({"game_id": g.id, "home": g.home_team_id, "away": g.away_team_id,
                        "events": [{"id": e.id, "q": e.quarter, "clk": e.clock, "t": e.event_type,
                                    "desc": (json.loads(e.description) if e.description else {}),
                                    "hs": e.score_home, "as": e.score_away} for e in evs]})
        return {"ok": True, "pbp": out}

@router.get("/team-stats/{season}/{week}")
def team_stats(season:int, week:int) -> dict:
    with session_scope() as s:
        games = s.exec(select(Game).where(Game.season==season, Game.week==week)).all()
        totals: Dict[int, Dict[str,int]] = {}
        for g in games:
            totals.setdefault(g.home_team_id, {"pass_yards":0,"rush_yards":0,"yards":0,"first_downs":0,"turnovers":0,"points":0})
            totals.setdefault(g.away_team_id, {"pass_yards":0,"rush_yards":0,"yards":0,"first_downs":0,"turnovers":0,"points":0})
            evs = s.exec(select(GameEvent).where(GameEvent.game_id==g.id)).all()
            for e in evs:
                d = {}
                if e.description:
                    try: d = json.loads(e.description)
                    except: d = {}
                if e.event_type == "play":
                    team = d.get("team")
                    yards = max(0, int(d.get("yards",0)))
                    tid = g.home_team_id if team == "home" else g.away_team_id
                    totals[tid]["yards"] += yards
                    if d.get("play") == "pass": totals[tid]["pass_yards"] += yards
                    else: totals[tid]["rush_yards"] += yards
                    if d.get("first_down"): totals[tid]["first_downs"] += 1
                elif e.event_type == "turnover":
                    team = d.get("team")
                    tid = g.home_team_id if team == "home" else g.away_team_id
                    totals[tid]["turnovers"] += 1
                elif e.event_type in ("td","fg","final"):
                    totals[g.home_team_id]["points"] = e.score_home
                    totals[g.away_team_id]["points"] = e.score_away
        rows = [{"team_id":tid, **vals} for tid, vals in totals.items()]
        rows.sort(key=lambda r: (r["points"], r["yards"]), reverse=True)
        return {"ok": True, "season": season, "week": week, "teams": rows}

@router.get("/standings/{season}")
def standings(season: int) -> dict:
    with session_scope() as s:
        teams = {t.id: t for t in s.exec(select(Team)).all()}
        table: Dict[int, Dict[str, Any]] = {tid: {"team_id": tid, "abbr": teams[tid].abbr,
                                                  "wins": 0, "losses": 0, "ties": 0, "pf": 0, "pa": 0}
                                            for tid in teams}
        games = s.exec(select(Game).where(Game.season == season, Game.status == "final")).all()
        for g in games:
            th = table[g.home_team_id]; ta = table[g.away_team_id]
            th["pf"] += g.home_score; th["pa"] += g.away_score
            ta["pf"] += g.away_score; ta["pa"] += g.home_score
            if g.home_score > g.away_score:
                th["wins"] += 1; ta["losses"] += 1
            elif g.home_score < g.away_score:
                ta["wins"] += 1; th["losses"] += 1
            else:
                th["ties"] += 1; ta["ties"] += 1
        rows: List[Dict[str, Any]] = []
        for tid, rec in table.items():
            diff = rec["pf"] - rec["pa"]
            power = 3.0 * rec["wins"] + diff / 50.0
            rec["power"] = round(power, 3)
            rows.append(rec)
        rows.sort(key=lambda r: (r["power"], r["wins"], r["pf"]), reverse=True)
        for i, r in enumerate(rows, start=1):
            r["rank"] = i
        return {"ok": True, "season": season, "standings": rows}

@router.get("/weeks/{season}")
def weeks_overview(season:int) -> dict:
    with session_scope() as s:
        out = {}
        for wk in range(1,19):
            games = s.exec(select(Game).where(Game.season==season, Game.week==wk)).all()
            finals = sum(1 for g in games if g.status=="final")
            out[wk] = {"scheduled": len(games), "finals": finals}
        return {"ok": True, "season": season, "weeks": out}


# === v2 realism helpers ===
from typing import List, Dict, Any, Tuple

def _cap(v:int, lo:int, hi:int) -> int:
    return max(lo, min(hi, v))

def _yardage_targets_v2(r:random.Random, rating_diff:float) -> Tuple[int,int,int,int]:
    """
    Per-team yard targets:
      - Total: mean ~340 (sd ~55), capped [220, 550]
      - Pass:Run ≈ 2.2:1 bounded to 1.6..2.8; pass capped ≤450
      - Rating diff nudges +/- up to ~30 yds
    """
    import math
    def norm(mu:int=340, sd:int=55) -> int:
        u,v = r.random(), r.random()
        z = ( (-2.0*math.log(max(u,1e-9)))**0.5 ) * math.cos(2*math.pi*v)
        return _cap(int(round(mu + sd*z)), 220, 550)

    yd_nudge = int(round(12 + 13*abs(rating_diff)))   # 12..~30
    sign = 1 if rating_diff >= 0 else -1
    ht = _cap(norm() + sign*yd_nudge, 220, 550)
    at = _cap(norm() - sign*yd_nudge, 220, 550)

    def split_pass(total:int) -> int:
        prx = _cap(int(round(10 * (2.2 + (r.random()-0.5)*0.8))), 16, 28) / 10.0  # 1.6..2.8
        py = int(round(total * (prx/(1+prx))))
        return _cap(py, 80, 450)

    hp = split_pass(ht)
    ap = split_pass(at)
    return ht, hp, at, ap

def _points_from_yards_v2(r:random.Random, home_yards:int, away_yards:int, exp_margin:float) -> Tuple[int,int]:
    """
    Yards → points via YPP in [13,20] (mode ~16). Apply a small margin shift.
    Caps single-team points to ~50.
    """
    def sample_ypp():
        # triangular(a=13, c=16, b=20)
        a,b,c = 13.0, 20.0, 16.0
        u = r.random()
        if u < (c-a)/(b-a):
            return a + ((b-a)*(c-a)*u)**0.5
        else:
            return b - ((b-a)*(b-c)*(1-u))**0.5

    hypp, aypp = sample_ypp(), sample_ypp()
    hpts = int(round(home_yards / hypp))
    apts = int(round(away_yards / aypp))

    shift = int(round(_cap(int(exp_margin), -7, 7) * 0.7))  # dampened HFA/ratings
    hpts = _cap(hpts + max(0, shift), 6, 50)
    apts = _cap(apts - max(0, shift), 6, 50)

    tot = hpts + apts
    if tot > 80:
        scale = 80 / tot
        hpts = _cap(int(round(hpts*scale)), 6, 50)
        apts = _cap(int(round(apts*scale)), 6, 50)
    return hpts, apts

def _compose_scoring_units_v2(r:random.Random, points:int) -> List[str]:
    """
    Convert target points to ["td","fg","safety"] mix; favors 7, then 3; rare safety.
    """
    out, p = [], points
    if p>=2 and r.random()<0.03:
        out.append("safety"); p -= 2
    while p >= 7:
        out.append("td"); p -= 7
        if r.random()<0.12 and p>=3: out.append("fg"); p -= 3
    if p>=3: out.append("fg"); p -= 3
    if p==2: out.append("safety")
    r.shuffle(out)
    return out

def _discrete_score_sim_v2(r:random.Random, exp_total:float, exp_margin:float,
                           home_target_pts:int, away_target_pts:int) -> Tuple[int,int, list]:
    """
    Target-aware score composer returning (home_points, away_points, events_list[('home'/'away', kind)]).
    """
    evs = [("home", e) for e in _compose_scoring_units_v2(r, home_target_pts)]
    evs += [("away", e) for e in _compose_scoring_units_v2(r, away_target_pts)]
    r.shuffle(evs)
    return home_target_pts, away_target_pts, evs

# ----- realistic drive/PBP with punts, sacks, typed turnovers, downs -----

def _drive_result_mix_v2(r: random.Random, target_punt_rate: float = 0.40) -> str:
    x = r.random()
    if x < target_punt_rate:
        return "punt"
    elif x < target_punt_rate + 0.10:
        return "turnover"
    else:
        return "score"

def _choose_turnover_type_v2(r: random.Random) -> str:
    return "interception" if r.random() < 0.65 else "fumble"

def _punt_distance_v2(r: random.Random) -> int:
    return int(r.uniform(42, 55))

def _return_yards_v2(r: random.Random) -> int:
    u = r.random()
    if u < 0.70: return int(r.uniform(0, 8))
    if u < 0.95: return int(r.uniform(8, 22))
    return int(r.uniform(22, 45))

def _play_clock_tick_v2(r: random.Random, was_pass: bool, incomplete: bool) -> int:
    if incomplete: return 0 if r.random() < 0.3 else int(r.uniform(3, 9))
    return int(r.uniform(19, 32))

def _simulate_pbp_for_game_v2(s, g:Game, season:int, week:int,
                              hs:int, as_:int, h_abbr:str, a_abbr:str,
                              h_total:int, h_pass:int, a_total:int, a_pass:int,
                              scoring_events:list) -> None:
    """
    - Every play has down & to_go.
    - Sacks as pass plays with is_sack=True (negative yards).
    - Punts with yards & return_yards.
    - Turnovers typed: interception/fumble; enforce ≥3 per game (soft).
    - ~40% drives end in punts. Score volume ~40–55 total.
    - Final 'final' event matches hs/as_ exactly.
    """
    from collections import deque

    r = _rng(g.home_team_id, g.away_team_id, season, week)
    sh, sa = 0, 0
    q, clock = 1, 900

    def emit_play(payload:Dict[str,Any]):
        nonlocal q, clock, sh, sa
        s.add(GameEvent(game_id=g.id, quarter=q, clock=f"{clock//60:02d}:{clock%60:02d}",
                        event_type="play", description=json.dumps(payload, separators=(",",":")),
                        score_home=sh, score_away=sa))
    def emit_evt(etype:str, payload:Dict[str,Any]):
        nonlocal q, clock, sh, sa
        s.add(GameEvent(game_id=g.id, quarter=q, clock=f"{clock//60:02d}:{clock%60:02d}",
                        event_type=etype, description=json.dumps(payload, separators=(",",":")),
                        score_home=sh, score_away=sa))

    budget = {
        "home": {"pass": max(0, h_pass), "rush": max(0, h_total - h_pass)},
        "away": {"pass": max(0, a_pass), "rush": max(0, a_total - a_pass)},
    }
    qscore = {"home": deque([k for who,k in scoring_events if who=="home"]),
              "away": deque([k for who,k in scoring_events if who=="away"])}

    def tick(sec:int):
        nonlocal q, clock
        clock = max(0, clock - sec)
        if clock == 0 and q < 4:
            q += 1; clock = 900

    forced_tos = 3
    offense = "home" if r.random() < 0.5 else "away"
    drives_total = r.randint(18, 24)

    for _drive in range(drives_total):
        team = offense; other = "away" if team=="home" else "home"
        down, to_go = 1, 10

        outcome = _drive_result_mix_v2(r, 0.40)
        if forced_tos > 0 and r.random() < 0.25:
            outcome = "turnover"; forced_tos -= 1

        score_kind = None
        if outcome == "score" and qscore[team]:
            score_kind = qscore[team][0]
        elif outcome == "score":
            outcome = "punt" if r.random()<0.8 else "turnover"

        snaps = r.randint(3, 8)
        for _ in range(snaps):
            want_pass = budget[team]["pass"] > budget[team]["rush"]
            pass_bias = 0.56 + (0.06 if want_pass else -0.04)
            is_pass = (r.random() < pass_bias)

            if is_pass:
                # sack chance
                if r.random() < 0.08 and budget[team]["pass"] > 0:
                    y = -int(r.uniform(3, 10))
                    emit_play({"team":team,"play":"pass","is_sack":True,"yards":y,"down":down,"to_go":to_go})
                    to_go = min(20, to_go - y)  # negative adds to_go
                    tick(_play_clock_tick_v2(r, True, False))
                else:
                    if r.random() < 0.35:
                        emit_play({"team":team,"play":"pass","is_sack":False,"yards":0,"down":down,"to_go":to_go,"complete":False})
                        tick(_play_clock_tick_v2(r, True, True))
                    else:
                        gain = int(r.uniform(3, 24))
                        gain = min(gain, budget[team]["pass"])
                        budget[team]["pass"] -= max(0, gain)
                        first = gain >= to_go
                        emit_play({"team":team,"play":"pass","is_sack":False,"yards":gain,"first_down":first,"down":down,"to_go":to_go,"complete":True})
                        if first: down, to_go = 1, 10
                        else:     to_go = max(1, to_go - gain)
                        tick(_play_clock_tick_v2(r, True, False))
            else:
                gain = int(r.uniform(-2, 12))
                gain = max(0, min(gain, budget[team]["rush"]))
                budget[team]["rush"] -= gain
                first = gain >= to_go
                emit_play({"team":team,"play":"run","yards":gain,"first_down":first,"down":down,"to_go":to_go})
                if first: down, to_go = 1, 10
                else:     to_go = max(1, to_go - gain)
                tick(_play_clock_tick_v2(r, False, False))

            if not (first if 'first' in locals() else False):
                down += 1

            # spontaneous turnover (rare)
            if outcome != "score" and r.random() < 0.02:
                outcome = "turnover"

            if down > 4:
                if outcome == "score" and score_kind == "fg":
                    if team == "home": sh += 3
                    else: sa += 3
                    emit_evt("fg", {"team":team,"good":True})
                    qscore[team].popleft()
                else:
                    pd, ret = _punt_distance_v2(r), _return_yards_v2(r)
                    emit_evt("punt", {"team":team,"yards":pd,"return_yards":ret})
                break

            if outcome == "turnover":
                ttype = _choose_turnover_type_v2(r)
                emit_evt("turnover", {"team":team,"type":ttype})
                break
        else:
            # Full snaps exhausted — apply outcome
            if outcome == "score" and score_kind:
                if score_kind == "td":
                    if team == "home": sh += 7
                    else: sa += 7
                    emit_evt("td", {"team":team,"type":"rush" if r.random()<0.5 else "pass"})
                    qscore[team].popleft()
                else:
                    if team == "home": sh += 3
                    else: sa += 3
                    emit_evt("fg", {"team":team,"good":True})
                    qscore[team].popleft()
            elif outcome == "turnover":
                ttype = _choose_turnover_type_v2(r)
                emit_evt("turnover", {"team":team,"type":ttype})
            else:
                pd, ret = _punt_distance_v2(r), _return_yards_v2(r)
                emit_evt("punt", {"team":team,"yards":pd,"return_yards":ret})

        offense = other
        tick(int(r.uniform(10, 35)))

    # lock in exact final
    sh, sa = hs, as_
    emit_evt("final", {"home":h_abbr,"away":a_abbr})
# === end v2 realism helpers ===
