# app/services/staff_service.py
from __future__ import annotations
from datetime import date
from typing import List, Tuple, Optional
from sqlmodel import Session, select
from app.models.coach import Coach, CoachContract, CoachRole, CoachFocus

# ---- Queries ----
def get_team_staff(sess: Session, team_id: int) -> List[Coach]:
    return list(sess.exec(select(Coach).where(Coach.team_id == team_id).order_by(Coach.role)).all())

def get_free_agent_coaches(sess: Session) -> List[Coach]:
    return list(sess.exec(select(Coach).where(Coach.team_id == None)).all())  # noqa: E711

def list_non_hc_on_other_teams(sess: Session) -> List[Coach]:
    return list(sess.exec(select(Coach).where(Coach.team_id != None, Coach.role != "HC")).all())  # noqa: E711

def get_active_contract(sess: Session, coach_id: int) -> Optional[CoachContract]:
    return sess.exec(select(CoachContract).where(CoachContract.coach_id == coach_id, CoachContract.is_active == True)).first()  # noqa: E712

# ---- Mutations ----
def hire_or_extend(sess: Session, coach: Coach, team_id: int, season: int, aav: int, years: int, via: str = "HIRE"):
    # end any active
    cur = get_active_contract(sess, coach.coach_id)
    if cur:
        cur.is_active = False
        sess.add(cur)
    coach.team_id = team_id
    sess.add(coach)
    sess.add(CoachContract(
        coach_id=coach.coach_id,
        team_id=team_id,
        signed_on=date.today(),
        start_season=season,
        end_season=season + years - 1,
        aav=aav,
        is_active=True,
        acquired_via=via
    ))
    sess.commit()

def fire_coach(sess: Session, coach_id: int):
    c = sess.get(Coach, coach_id)
    if not c:
        raise ValueError("COACH_NOT_FOUND")
    cur = get_active_contract(sess, coach_id)
    if cur:
        cur.is_active = False
        sess.add(cur)
    # move to FA pool
    c.team_id = None
    c.role = "AC"  # neutralize role in FA; can be hired/promoted later
    c.weeks_focus_bank = 0
    sess.add(c)
    sess.commit()

def promote(sess: Session, coach_id: int, new_role: CoachRole, season: int):
    c = sess.get(Coach, coach_id)
    if not c:
        raise ValueError("COACH_NOT_FOUND")
    # role gate
    if new_role == "HC":
        if c.role not in ("OC","DC","AC"):
            raise ValueError("PROMOTION_PATH_INVALID")
    elif new_role in ("OC","DC"):
        if c.role != "AC":
            raise ValueError("PROMOTION_PATH_INVALID")
    else:
        raise ValueError("PROMOTION_TO_AC_NOT_SUPPORTED")  # keep AC hiring rather than promoting down

    c.role = new_role
    sess.add(c)
    sess.commit()

def set_coach_focus(sess: Session, coach_id: int, focus: CoachFocus):
    c = sess.get(Coach, coach_id)
    if not c:
        raise ValueError("COACH_NOT_FOUND")
    c.focus = focus
    sess.add(c)
    sess.commit()

def tally_coach_focus_for_week(sess: Session, team_id: int):
    """Call once per week end. Adds +1 to every staff member's weeks_focus_bank based on their current focus."""
    staff = get_team_staff(sess, team_id)
    for c in staff:
        c.weeks_focus_bank += 1
        sess.add(c)
    sess.commit()


