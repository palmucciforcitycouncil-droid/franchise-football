# app/services/coach_ai.py
from __future__ import annotations
import random
from dataclasses import dataclass
from typing import Literal, Iterable
from sqlmodel import Session, select
from app.models.coach import Coach, CoachContract, CoachRole

@dataclass
class Offer:
    aav: int
    years: int

def coach_accepts(offer: Offer, coach: Coach, promotion: bool) -> bool:
    """
    MVP acceptance:
      - Baseline ask = rating tier * role multiplier.
      - If offer >= 96% of ask AAV and years >= 2 (HC) / >=1 (others) → accept.
      - Promotion (e.g., OC->HC) reduces threshold by 4% (more likely to accept).
    """
    role_mult = {"HC": 1.40, "OC": 1.10, "DC": 1.10, "AC": 0.70}[coach.role if not promotion else "HC"]
    rating_tier = max(0, coach.overall - 60)  # 60–99 → 0–39
    ask_aav = int((2_000_000 + rating_tier * 120_000) * role_mult)
    threshold = 0.96 - (0.04 if promotion else 0.0)
    min_years = 2 if (coach.role == "HC" or promotion) else 1
    return (offer.aav >= int(ask_aav * threshold)) and (offer.years >= min_years)

def offseason_fill_vacancies(sess: Session, team_id: int, vacancies: Iterable[CoachRole], season: int, rng: random.Random):
    """
    Simple AI: hire best available by rating within budget envelope. Promotion priority:
    - If HC vacant: try to poach other team OC/DC/AC for HC if they accept (promotion = True).
    - Else OC/DC vacant: try to poach AC for promotion or sign FA coaches.
    """
    for role in vacancies:
        candidates = []
        if role == "HC":
            # Non-HC coaches on other teams are promotion candidates
            candidates.extend(sess.exec(select(Coach).where(Coach.team_id != None, Coach.role != "HC")).all())  # noqa: E711
            candidates.extend(sess.exec(select(Coach).where(Coach.team_id == None)).all())  # FA
        else:
            # Fill OC/DC with AC promotion or FA
            candidates.extend(sess.exec(select(Coach).where(Coach.team_id == None)).all())  # FA
            candidates.extend(sess.exec(select(Coach).where(Coach.team_id != None, Coach.role == "AC")).all())  # noqa: E711

        candidates.sort(key=lambda c: c.overall, reverse=True)
        if not candidates:
            continue

        top = candidates[0]
        promotion = (role == "HC" and top.role != "HC") or (role in ("OC","DC") and top.role == "AC")
        # Make a market-ish offer
        base_aav = int((2_200_000 + (top.overall - 60) * 140_000) * (1.40 if role=="HC" else (1.10 if role in ("OC","DC") else 0.70)))
        years = 4 if role == "HC" else 3
        if coach_accepts(Offer(base_aav, years), top, promotion):
            # Assign team and role; contract created elsewhere by service.hire_or_extend
            top.role = role
            sess.add(top)
            sess.commit()
            # The caller should then call hire_or_extend(...)


