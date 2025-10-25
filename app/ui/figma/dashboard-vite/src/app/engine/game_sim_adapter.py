# app/engine/game_sim_adapter.py
from sqlmodel import Session
from app.services.coach_modifiers import compute_team_modifiers

def get_team_sim_mods(sess: Session, team_id: int) -> dict[str, float]:
    m = compute_team_modifiers(sess, team_id)
    return {
        "offense_eff": m.off_gameplan,       # add to offense EPA/yd success adjustments
        "defense_eff": m.def_gameplan,       # subtract from opponent success
        "two_min_bonus": m.two_min_offense,  # increase prob of late scores
        "st_bonus": m.special_teams,
        "discipline_bonus": m.discipline,    # fewer penalties
        "stamina_injury": m.stamina_injury,  # reduce injury chance / duration
    }


