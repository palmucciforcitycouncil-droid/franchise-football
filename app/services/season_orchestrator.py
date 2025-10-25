from __future__ import annotations
from typing import Dict, Any, List, Optional
from random import Random
from sqlmodel import Session, select
from app.models.sim_models import Game
from app.services.event_log_service import emit_event
from app.services.results_service import week_scoreboard
from app.services.results_pipeline import on_game_final
from app.engine.results_hooks import persist_full_game
from app.services.depth_chart_service import lineup_for_game
from app.services.standings_service import _get_or_init as _get_or_init_stand

# Optional imports; orchestrator will use a fallback if your engine not present
def _try(path: str, name: str):
    try:
        mod = __import__(path, fromlist=[name]); return getattr(mod, name)
    except Exception:
        return None

simulate_game = _try("app.engine.game_sim", "simulate_game")  # expected signature below
Team = _try("app.models.team", "Team")

def _team_power(sess: Session, season: int, team_id: int) -> float:
    s = _get_or_init_stand(sess, season, team_id)
    return getattr(s, "power_rating", 1500.0)

def _fallback_sim(sess: Session, season: int, week: int, game_id: int, home_team_id: int, away_team_id: int, seed: int) -> Dict[str, Any]:
    """
    Deterministic, quick sim using Power Rating and RNG. Returns result + minimal team/player boxes.
    """
    rnd = Random(seed + game_id * 17)
    pr_home = _team_power(sess, season, home_team_id) + 55.0   # home edge
    pr_away = _team_power(sess, season, away_team_id)
    p_home = 1.0 / (1.0 + 10 ** (-(pr_home - pr_away)/400))
    # Draw a score with light spread
    home = int(17 + rnd.gauss(10 * p_home, 7))
    away = int(17 + rnd.gauss(10 * (1-p_home), 7))
    home = max(6, home); away = max(3, away)

    # Minimal team lines
    home_line = {"team_id": home_team_id, "yards_offense": max(200, int(home*25)), "pass_yds": int(home*0.6*15), "rush_yds": int(home*0.4*10),
                 "takeaways": rnd.randint(0,3), "giveaways": rnd.randint(0,3), "sacks": rnd.randint(0,5),
                 "third_down_pct": min(0.75, max(0.2, rnd.random() * 0.6)), "red_zone_td_pct": min(1.0, max(0.2, rnd.random())),
                 "time_of_possession_sec": rnd.randint(1500, 2100)}
    away_line = {"team_id": away_team_id, "yards_offense": max(180, int(away*24)), "pass_yds": int(away*0.6*14), "rush_yds": int(away*0.4*9),
                 "takeaways": rnd.randint(0,3), "giveaways": rnd.randint(0,3), "sacks": rnd.randint(0,5),
                 "third_down_pct": min(0.75, max(0.2, rnd.random() * 0.6)), "red_zone_td_pct": min(1.0, max(0.2, rnd.random())),
                 "time_of_possession_sec": rnd.randint(1500, 2100)}

    # No player boxes in fallback (keep simple)
    return {
        "home_score": home, "away_score": away,
        "home_team_line": home_line, "away_team_line": away_line,
        "player_boxes": []
    }

def sim_week(sess: Session, *, season: int, week: int, seed: int = 12345) -> Dict[str, Any]:
    """
    Simulate all scheduled games for (season, week).
    - Builds lineups (auto if missing).
    - Calls engine simulate_game if available, else fallback.
    - Persists results/boxes, updates standings/bracket, and emits events.
    Returns a summary with game_ids and scores.
    """
    games = list(sess.exec(select(Game).where(Game.season==season, Game.week==week)))
    if not games:
        return {"ok": True, "games": []}

    summary = []
    for g in games:
        # Ensure lineups exist (opponent needed for availability filters)
        lineup_for_game(sess, g.home_team_id, season, week, g.id, g.away_team_id)
        lineup_for_game(sess, g.away_team_id, season, week, g.id, g.home_team_id)

        if simulate_game:
            # Expected: simulate_game(sess, season, week, game_id, home_team_id, away_team_id) -> dict like fallback
            res = simulate_game(sess, season, week)  # type: ignore
        else:
            res = _fallback_sim(sess, season, week, g.id, g.home_team_id, g.away_team_id, seed)

        persist_full_game(
            sess, season=season, week=week, game_id=g.id,
            home_score=res["home_score"], away_score=res["away_score"],
            home_team_line=res["home_team_line"], away_team_line=res["away_team_line"],
            player_boxes=res.get("player_boxes", [])
        )

        # Standings/PR updates, bracket at week 18 handled here
        on_game_final(sess, season, g.id, week)

        # Emit event
        emit_event(sess, season=season, week=week, event_type="GAME_FINAL", game_id=g.id, payload={
            "home_team_id": g.home_team_id, "away_team_id": g.away_team_id,
            "home_score": res["home_score"], "away_score": res["away_score"]
        })

        summary.append({"game_id": g.id, "home": g.home_team_id, "away": g.away_team_id,
                        "home_score": res["home_score"], "away_score": res["away_score"]})

    # Hook: weekly awards (call your awards service if available)
    try:
        from app.services.awards_service import compute_weekly_awards
        compute_weekly_awards(sess, season=season, week=week)
        emit_event(sess, season=season, week=week, event_type="AWARD_WEEKLY", payload={"season": season, "week": week})
    except Exception:
        pass

    return {"ok": True, "games": summary}
