# app/services/negotiation_logic.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
from sqlmodel import Session
from app.models.core_min import Player

# Simple reasoned sliders
POS_MULT = {
    "QB": 1.30, "WR": 1.10, "LT": 1.10, "EDGE": 1.10, "CB": 1.05,
    "TE": 1.00, "IDL": 1.00, "S": 0.95, "LB": 0.95, "G": 0.95, "C": 0.95, "RT": 0.95,
    "RB": 0.85, "K": 0.60, "P": 0.55,
}

@dataclass
class OfferDecision:
    will_pay: bool
    offered_aav: int
    offered_years: int
    reason: Literal["core_piece","price_ok","too_old","too_expensive","cap_tight","depth_replaceable"]

def player_accepts(offered_aav: int, offered_years: int, player: Player) -> bool:
    # MVP: accept if >= 96% of ask and within 1 year of desired
    return (offered_aav >= int(player.desired_aav * 0.96)) and (offered_years >= max(1, player.desired_years - 1))

def ai_offer_for_player(player: Player, team_cap_space: int) -> OfferDecision:
    pos_factor = POS_MULT.get(player.pos, 1.0)
    age_penalty = max(0.0, (player.age - 29) * 0.03)           # 3% per year >29
    ovr_bonus = max(0.0, (player.rating - 84) * 0.02)         # 2% per OVR above 84
    base_inclination = 0.70*pos_factor + 0.30*ovr_bonus - age_penalty

    affordable = player.desired_aav <= max(1_000_000, int(team_cap_space * 0.25))
    if not affordable:
        return OfferDecision(False, 0, 0, "cap_tight")

    haircut = 0.0 if base_inclination >= 1.0 else (1.0 - base_inclination) * 0.15
    offered_aav = int(player.desired_aav * (1 - haircut))
    offered_years = max(1, min(player.desired_years, 5))

    will_pay = base_inclination >= 0.85
    reason = "core_piece" if player.rating >= 90 else ("price_ok" if haircut == 0.0 else ("too_old" if age_penalty > 0.12 else "depth_replaceable"))
    return OfferDecision(will_pay, offered_aav, offered_years, reason)


