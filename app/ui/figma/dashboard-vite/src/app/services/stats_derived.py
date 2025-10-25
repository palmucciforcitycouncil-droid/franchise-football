# app/services/stats_derived.py
from __future__ import annotations
from typing import Dict, Tuple

def _safe_div(n: float, d: float) -> float:
    """Safe division that returns 0.0 if denominator is 0."""
    return float(n) / float(d) if d else 0.0

def derive_passing(stats: Dict[str, float]) -> Dict[str, float]:
    """Derive passing metrics from raw stats."""
    att, cmp_, yds, td, it, sacks = (stats.get(k,0) for k in ("pass_att","pass_cmp","pass_yds","pass_td","pass_int","sacks_taken"))
    dropbacks = att + sacks
    res = {
        "cmp_pct": _safe_div(cmp_, att),
        "yds_per_att": _safe_div(yds, att),
        "yds_per_cmp": _safe_div(yds, cmp_),
        "td_pct": _safe_div(td, att),
        "int_pct": _safe_div(it, att),
        "sack_rate": _safe_div(sacks, dropbacks),
        "air_yds_share": _safe_div(stats.get("air_yds",0), max(1, yds)),
        "yac_share": _safe_div(stats.get("yac_gained",0), max(1, yds)),
        "deep_att_rate": _safe_div(stats.get("deep_att",0), max(1, att)),
        "play_action_rate": _safe_div(stats.get("play_action_att",0), max(1, att)),
        "screen_rate": _safe_div(stats.get("screen_att",0), max(1, att)),
        "pressure_rate": _safe_div(stats.get("pressure_dropbacks",0), max(1, dropbacks)),
        "hit_rate": _safe_div(stats.get("hits_on_qb",0), max(1, dropbacks)),
        "throwaway_rate": _safe_div(stats.get("throwaways",0), max(1, dropbacks)),
        "batted_rate": _safe_div(stats.get("batted_passes",0), max(1, att)),
        "drop_rate_against_qb": _safe_div(stats.get("drops_forced",0), max(1, stats.get("tar",0))),
    }
    # NFL passer rating (optional basic)
    a = max(0,min((_safe_div(cmp_, att) - .3)*5, 2.375))
    b = max(0,min((_safe_div(yds, att) - 3)*0.25, 2.375))
    c = max(0,min((_safe_div(td, att))*20, 2.375))
    d = max(0,min((2.375 - (_safe_div(it, att)*25)), 2.375))
    res["passer_rating"] = ((a+b+c+d)/6)*100 if att else 0.0
    return res

def derive_rushing(stats: Dict[str, float]) -> Dict[str, float]:
    """Derive rushing metrics from raw stats."""
    att, yds, td = (stats.get(k,0) for k in ("rush_att","rush_yds","rush_td"))
    ybc = stats.get("yards_before_contact",0)
    yac = stats.get("yards_after_contact",0)
    return {
        "yds_per_rush": _safe_div(yds, att),
        "td_rate_rush": _safe_div(td, att),
        "yards_before_contact_per_att": _safe_div(ybc, att),
        "yards_after_contact_per_att": _safe_div(yac, att),
        "designed_rush_share": _safe_div(stats.get("designed_rush_att",0), max(1, att)),
        "scramble_share": _safe_div(stats.get("scramble_att",0), max(1, att)),
    }

def derive_receiving(stats: Dict[str, float]) -> Dict[str, float]:
    """Derive receiving metrics from raw stats."""
    tar, rec, yds, td = (stats.get(k,0) for k in ("tar","rec","rec_yds","rec_td"))
    air_for = stats.get("air_yds_for",0)
    yac = stats.get("yac",0)
    return {
        "catch_pct": _safe_div(rec, tar),
        "yds_per_rec": _safe_div(yds, rec),
        "yds_per_target": _safe_div(yds, tar),
        "td_per_target": _safe_div(td, tar),
        "air_yds_share_for": _safe_div(air_for, max(1, yds)),
        "yac_per_rec": _safe_div(yac, rec),
        "contested_catch_rate": _safe_div(stats.get("contested_catches_won",0), max(1, rec)),
        "deep_target_rate": _safe_div(stats.get("receptions_deep",0), max(1, rec)),
    }

def derive_ball_security(stats: Dict[str, float], touches: int) -> Dict[str, float]:
    """Derive ball security metrics from raw stats."""
    fum = stats.get("fumbles",0); lost = stats.get("fumbles_lost",0)
    return {
        "fumbles_per_touch": _safe_div(fum, max(1, touches)),
        "lost_fumbles_per_touch": _safe_div(lost, max(1, touches)),
    }

def derive_defense(stats: Dict[str, float]) -> Dict[str, float]:
    """Derive defensive metrics from raw stats."""
    tackles = stats.get("tackles",0)
    missed = stats.get("missed_tackles",0)
    pressures = stats.get("pressures",0)
    sacks = stats.get("sacks",0.0)
    pd_snaps = stats.get("targets_defended",0)
    comp_allowed = stats.get("receptions_allowed",0)
    yards_allowed = stats.get("rec_yds_allowed",0)
    yacs_allowed = stats.get("yacs_allowed",0)
    return {
        "missed_tackle_rate": _safe_div(missed, max(1, tackles + missed)),
        "pressures_per_pass_snap": _safe_div(pressures, max(1, pd_snaps)),  # proxy if you store pass-rush snaps later
        "pressure_conversion_rate": _safe_div(sacks, max(1.0, pressures)),
        "comp_allowed_pct": _safe_div(comp_allowed, max(1, pd_snaps)),
        "yards_per_target_allowed": _safe_div(yards_allowed, max(1, pd_snaps)),
        "yacs_allowed_per_rec": _safe_div(yacs_allowed, max(1, comp_allowed)),
        "takeaways": stats.get("ints",0) + stats.get("fr",0),
        "penalty_rate_def": _safe_div(stats.get("penalties_committed_def",0), max(1, pd_snaps)),
    }

def derive_special_teams(stats: Dict[str, float]) -> Dict[str, float]:
    """Derive special teams metrics from raw stats."""
    fg_made = stats.get("fg_made",0); fg_att = stats.get("fg_att",0)
    xp_made = stats.get("xp_made",0); xp_att = stats.get("xp_att",0)
    punts = stats.get("punts",0); punt_yds = stats.get("punt_yds",0)
    pr_allowed = stats.get("punt_returns_allowed",0); pry_allowed = stats.get("punt_return_yds_allowed",0)
    kickoffs = stats.get("kickoffs",0); touchbacks = stats.get("touchbacks",0)
    kr = stats.get("kr",0); kry = stats.get("kr_yds",0); krt = stats.get("kr_td",0)
    pr = stats.get("pr",0); pry = stats.get("pr_yds",0); prt = stats.get("pr_td",0)
    res = {
        "fg_pct": _safe_div(fg_made, fg_att),
        "xp_pct": _safe_div(xp_made, xp_att),
        "gross_punt_avg": _safe_div(punt_yds, max(1, punts)),
        "net_punt_avg": _safe_div((punt_yds - pry_allowed), max(1, punts)),
        "inside_20_rate": _safe_div(stats.get("punts_inside_20",0), max(1, punts)),
        "punt_touchback_rate": _safe_div(stats.get("punt_touchbacks",0), max(1, punts)),
        "touchback_rate": _safe_div(touchbacks, max(1, kickoffs)),
        "avg_kickoff_depth": stats.get("avg_kickoff_yds", 0.0),
        "kr_avg": _safe_div(kry, max(1, kr)),
        "pr_avg": _safe_div(pry, max(1, pr)),
        "return_td_rate": _safe_div(krt + prt, max(1, kr + pr)),
        "st_tackle_rate": _safe_div(stats.get("st_tackles",0), max(1, stats.get("snaps_st",0))),
        "st_missed_tackle_rate": _safe_div(stats.get("st_missed_tackles",0), max(1, stats.get("snaps_st",0))),
    }
    res["fg_long"] = stats.get("long_fg_made",0)
    return res

def derive_participation(stats: Dict[str, float], team_snaps: Tuple[int,int,int] | None = None) -> Dict[str, float]:
    """Derive participation metrics from raw stats."""
    so, sd, ss = (stats.get("snaps_off",0), stats.get("snaps_def",0), stats.get("snaps_st",0))
    to, td, ts = team_snaps if team_snaps else (0,0,0)
    return {
        "snap_share_off": _safe_div(so, max(1, to or so)),
        "snap_share_def": _safe_div(sd, max(1, td or sd)),
        "snap_share_st":  _safe_div(ss, max(1, ts or ss)),
        "games_active_pct": _safe_div(stats.get("games_played",0), max(1, stats.get("games_played",0))),  # trivial now
        "starts_rate": _safe_div(stats.get("games_started",0), max(1, stats.get("games_played",0))),
    }

def derive_all(stats: Dict[str, float], touches: int, team_snaps: Tuple[int,int,int] | None = None) -> Dict[str, float]:
    """Derive all metrics from raw stats."""
    out = {}
    out |= derive_passing(stats)
    out |= derive_rushing(stats)
    out |= derive_receiving(stats)
    out |= derive_ball_security(stats, touches)
    out |= derive_defense(stats)
    out |= derive_special_teams(stats)
    out |= derive_participation(stats, team_snaps)
    return out


