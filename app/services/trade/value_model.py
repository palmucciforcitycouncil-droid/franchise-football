from typing import Dict
from .schemas import AssetValue, EvaluationInputs
from .calibrations import PICK_ROUND_BASE, PICK_ROUND_SPREAD, AGE_DECAY_START, QB_AGE_DECAY_START

def _age_decay(position: str, age: int, w_age_decay: float) -> float:
    """Compute age penalty for a player."""
    start = QB_AGE_DECAY_START if position == "QB" else AGE_DECAY_START
    excess = max(0, age - start)
    return -w_age_decay * excess

def player_base_value(position: str, ovr: int, potential: int, age: int, contract_years: int, aav: int, inputs: EvaluationInputs) -> AssetValue:
    """Calculate base value for a player asset."""
    bv = (inputs.w_player_ovr * ovr + 
          inputs.w_potential * (potential - 50) + 
          _age_decay(position, age, inputs.w_age_decay) * 10)
    
    contract_penalty = (inputs.w_contract_years * max(0, -(contract_years - 1)) + 
                       inputs.w_contract_cost * aav)
    
    net = max(0.0, bv - contract_penalty)
    
    return AssetValue(
        asset_type="PLAYER",
        asset_id=None,
        base_value=bv,
        contract_penalty=contract_penalty,
        net_value=net
    )

def pick_value(season: int, round_: int, current_year: int, inputs: EvaluationInputs) -> AssetValue:
    """Calculate value for a draft pick."""
    base = PICK_ROUND_BASE.get(round_, inputs.w_pick_round_base)
    spread = PICK_ROUND_SPREAD.get(round_, 2)
    years_out = max(0, season - current_year)
    discount = (1.0 - inputs.w_pick_year_discount) ** years_out
    net = (base + spread/2) * discount
    
    return AssetValue(
        asset_type="PICK",
        pick={"season": season, "round": round_},
        base_value=base,
        net_value=net
    )

def apply_need_fit(position: str, net_value: float, team_need: float, inputs: EvaluationInputs) -> float:
    """Apply team need bonus to asset value."""
    return net_value + inputs.w_need_fit * team_need
