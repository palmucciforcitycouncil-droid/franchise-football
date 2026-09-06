"""
Typer CLI commands for Advanced Stats operations.
Commands for rollup, materialize, validate, and dump JSON reports.
"""

import typer
import json
import os
from typing import Optional
from sqlmodel import Session
from app.services.stats.rollup import rollup_game_stats
from app.services.stats.materialize import materialize_season, materialize_career
from app.services.stats.validators import validate_game_totals
from app.services.stats.read import get_game_box

app = typer.Typer(name="stats", help="Advanced Stats CLI commands")


def get_session():
    """Get database session - simplified for now"""
    # In a real implementation, this would get the actual session
    return None


@app.command("rollup")
def rollup(
    game: int = typer.Option(..., "--game", help="Game ID"),
    session: Optional[Session] = None
):
    """Roll up game stats from PBP events."""
    if session is None:
        session = get_session()
    
    try:
        result = rollup_game_stats(game, session)
        typer.echo(f"Rolled up game {game}")
        typer.echo(f"Events processed: {result['events_processed']}")
        typer.echo(f"Player stats created: {result['player_stats_created']}")
        typer.echo(f"Player stats updated: {result['player_stats_updated']}")
        typer.echo(f"Team stats created: {result['team_stats_created']}")
        typer.echo(f"Team stats updated: {result['team_stats_updated']}")
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(1)


@app.command("materialize")
def materialize(
    scope: str = typer.Option(..., "--scope", help="season|career"),
    year: Optional[int] = typer.Option(None, "--year"),
    session: Optional[Session] = None
):
    """Materialize season or career stats."""
    if session is None:
        session = get_session()
    
    try:
        if scope == "season":
            if year is None:
                typer.echo("Error: --year is required for season materialization", err=True)
                raise typer.Exit(1)
            result = materialize_season(year, session)
            typer.echo(f"Materialized season {year}")
            typer.echo(f"Games processed: {result['games_processed']}")
            typer.echo(f"Player season stats created: {result['player_season_stats_created']}")
            typer.echo(f"Player season stats updated: {result['player_season_stats_updated']}")
            typer.echo(f"Team season stats created: {result['team_season_stats_created']}")
            typer.echo(f"Team season stats updated: {result['team_season_stats_updated']}")
        elif scope == "career":
            result = materialize_career(session)
            typer.echo("Materialized career stats")
            typer.echo(f"Seasons processed: {result['seasons_processed']}")
            typer.echo(f"Player career stats created: {result['player_career_stats_created']}")
        else:
            typer.echo("Error: scope must be 'season' or 'career'", err=True)
            raise typer.Exit(1)
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(1)


@app.command("validate")
def validate(
    game: Optional[int] = typer.Option(None, "--game"),
    session: Optional[Session] = None
):
    """Validate stats consistency."""
    if session is None:
        session = get_session()
    
    try:
        messages = validate_game_totals(game, session)
        
        if not messages:
            typer.echo("Validation complete - no issues found.")
        else:
            typer.echo(f"Validation complete - {len(messages)} messages:")
            
            errors = [m for m in messages if m.level == "error"]
            warnings = [m for m in messages if m.level == "warning"]
            infos = [m for m in messages if m.level == "info"]
            
            if errors:
                typer.echo(f"\nErrors ({len(errors)}):")
                for msg in errors:
                    typer.echo(f"  ERROR [{msg.category}]: {msg.message}")
            
            if warnings:
                typer.echo(f"\nWarnings ({len(warnings)}):")
                for msg in warnings:
                    typer.echo(f"  WARNING [{msg.category}]: {msg.message}")
            
            if infos:
                typer.echo(f"\nInfo ({len(infos)}):")
                for msg in infos:
                    typer.echo(f"  INFO [{msg.category}]: {msg.message}")
        
        typer.echo("Validation complete.")
        
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(1)


@app.command("dump-game-report")
def dump_game_report(
    game: int = typer.Option(..., "--game"),
    outdir: str = typer.Option("data/reports", "--outdir"),
    session: Optional[Session] = None
):
    """Dump game box score to JSON report."""
    if session is None:
        session = get_session()
    
    try:
        os.makedirs(outdir, exist_ok=True)
        box = get_game_box(game, session)
        
        if not box:
            typer.echo(f"Error: Game {game} not found", err=True)
            raise typer.Exit(1)
        
        path = os.path.join(outdir, f"game_{game}_boxscore.json")
        
        # Convert to dict for JSON serialization
        box_dict = box.dict() if hasattr(box, "dict") else box
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(box_dict, f, ensure_ascii=False, indent=2)
        
        typer.echo(f"Wrote {path}")
        
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(1)


@app.command("dump-season-report")
def dump_season_report(
    year: int = typer.Option(..., "--year"),
    outdir: str = typer.Option("data/reports", "--outdir"),
    session: Optional[Session] = None
):
    """Dump season stats to JSON report."""
    if session is None:
        session = get_session()
    
    try:
        os.makedirs(outdir, exist_ok=True)
        
        # Get team season stats
        from app.services.stats.read import get_team_season_lines
        team_stats = get_team_season_lines(year=year, session=session)
        
        path = os.path.join(outdir, f"season_{year}_team_stats.json")
        
        # Convert to dict for JSON serialization
        team_stats_dict = [stat.dict() if hasattr(stat, "dict") else stat for stat in team_stats]
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(team_stats_dict, f, ensure_ascii=False, indent=2)
        
        typer.echo(f"Wrote {path}")
        
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(1)


@app.command("dump-career-report")
def dump_career_report(
    outdir: str = typer.Option("data/reports", "--outdir"),
    session: Optional[Session] = None
):
    """Dump career leaders to JSON report."""
    if session is None:
        session = get_session()
    
    try:
        os.makedirs(outdir, exist_ok=True)
        
        # Get career leaders for key stats
        from app.services.stats.read import get_leaders
        
        career_stats = {}
        key_stats = [
            "passing_yards", "passing_touchdowns", "rushing_yards", "rushing_touchdowns",
            "receiving_yards", "receiving_touchdowns", "tackles", "sacks", "interceptions_caught"
        ]
        
        for stat in key_stats:
            leaders = get_leaders(stat=stat, top=10, session=session)
            career_stats[stat] = leaders.dict() if hasattr(leaders, "dict") else leaders
        
        path = os.path.join(outdir, "player_career_leaders.json")
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(career_stats, f, ensure_ascii=False, indent=2)
        
        typer.echo(f"Wrote {path}")
        
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
