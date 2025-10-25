# app/services/awards_pipeline.py
from __future__ import annotations
from sqlmodel import Session
from app.services.awards_compute import compute_weekly_awards, compute_annual_projections, finalize_annual_awards

def on_week_complete(sess: Session, season: int, week: int):
    """Process awards after a week is completed."""
    compute_weekly_awards(sess, season, week)
    compute_annual_projections(sess, season)

def on_season_finalized(sess: Session, season: int):
    """Process awards after a season is finalized (post-playoffs)."""
    finalize_annual_awards(sess, season)


