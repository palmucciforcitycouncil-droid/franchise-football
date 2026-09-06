# app/engine/annual_progression.py
from app.services.coach_modifiers import compute_team_modifiers

def apply_coach_development_effect(sess, team_id, player_list):
    mods = compute_team_modifiers(sess, team_id)
    for p in player_list:
        # Add small development boost to player progression
        if hasattr(p, 'progression_delta'):
            p.progression_delta += mods.development
        # Alternative: add to potential or other development-related attributes
        if hasattr(p, 'potential') and mods.development > 0:
            p.potential = min(99, p.potential + int(mods.development * 0.1))


