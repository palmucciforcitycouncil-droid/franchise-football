"""
Season Export Service.
"""

from __future__ import annotations
from typing import Dict, Any, List
from pathlib import Path
import json
from sqlmodel import Session, select

from app.services.awards import compute_season_awards, compute_league_leaders
from app.services.weekly_awards import compute_weekly_awards
from app.models.awards import AwardWinner
from app.models.weekly_awards import WeeklyAward


def _safe_dir(p: Path):
    """Ensure directory exists."""
    p.parent.mkdir(parents=True, exist_ok=True)


def _try_fetch_standings(session: Session, season: int) -> List[Dict[str, Any]]:
    """Try to fetch team standings."""
    # Try to find a TeamSeason table/service
    for mod, name in [
        ("app.models.stats_models", "TeamSeasonStats"),
    ]:
        try:
            m = __import__(mod, fromlist=[name])
            TS = getattr(m, name)
            rows = session.exec(select(TS)).all()
            return [r.__dict__.copy() for r in rows]
        except Exception:
            continue
    return []


def export_season_summary(session: Session, season: int, out_json: str = "data/reports/season_summary.json", out_html: str = "data/reports/season_summary.html") -> Dict[str, Any]:
    """Export season summary to JSON and optionally HTML."""
    # Compute (or fetch) season awards + weekly awards + league leaders + standings
    try:
        season_awards = compute_season_awards(session, season)
    except Exception:
        season_awards = {}
    
    try:
        weekly_awards = compute_weekly_awards(session, season)
    except Exception:
        weekly_awards = []
    
    try:
        leaders = compute_league_leaders(session, season, top_n=10)
    except Exception:
        leaders = []
    
    standings = _try_fetch_standings(session, season)

    # Materialize persisted awards for traceability
    try:
        aw_rows = session.exec(select(AwardWinner).where(AwardWinner.season == season)).all()
    except Exception:
        aw_rows = []
    
    try:
        w_rows = session.exec(select(WeeklyAward).where(WeeklyAward.season == season)).all()
    except Exception:
        w_rows = []

    # Convert SQLModel objects to dictionaries for JSON serialization
    def to_dict(obj):
        if hasattr(obj, '__dict__'):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
        return obj

    payload = {
        "season": season,
        "standings": standings,
        "awards": season_awards,
        "awards_persisted": [to_dict(r) for r in aw_rows],
        "weekly_awards": [to_dict(r) for r in w_rows],
        "leaders": [
            {
                "title": b.title,
                "leaders": [{"name": lr.name, "player_id": lr.player_id, "team_id": lr.team_id, "value": lr.value} for lr in b.leaders]
            } for b in leaders
        ],
    }

    # Write JSON
    outp = Path(out_json)
    _safe_dir(outp)
    with outp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    # Optional HTML if Jinja2 is installed and a template exists
    try:
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        env = Environment(loader=FileSystemLoader("app/templates"), autoescape=select_autoescape())
        tpl = env.get_template("season_summary.html.j2")
        html = tpl.render(**payload)
        outh = Path(out_html)
        _safe_dir(outh)
        outh.write_text(html, encoding="utf-8")
    except Exception:
        pass

    return payload
