from typing import Dict, Tuple
from .schemas import TradeOffer, EvaluationInputs

def would_break_minimums(team_counts_after: Dict[str,int], soft_mins: Dict[str,int]) -> Tuple[bool,str]:
    """Hard veto if QB/K/P minimums broken; warn for others."""
    for k in ["QB","K","P"]:
        if team_counts_after.get(k,0) < soft_mins.get(k,1):
            return True, f"Leaves team without required {k}"
    return False, ""

def cap_ok(cap_space_after: int) -> bool:
    return cap_space_after >= 0

def hard_veto_reason(offer: TradeOffer, team_counts_after, cap_space_after, inputs: EvaluationInputs) -> str | None:
    breaks, msg = would_break_minimums(team_counts_after, inputs.soft_minimums)
    if breaks:
        return msg
    if not cap_ok(cap_space_after):
        return "Violates salary cap space"
    return None
