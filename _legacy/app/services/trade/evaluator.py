"""Main trade evaluation logic for CPU decision making."""
from __future__ import annotations
from typing import Dict, List
from sqlmodel import Session
from .schemas import TradeOffer, EvaluationInputs, EvaluationResult, TradeSide
from .value_model import player_base_value, pick_value, apply_need_fit
from .rules import hard_veto_reason
from .calibrations import CRITICAL_POS
from . import _adapters

def evaluate_trade(
    sess: Session,
    offer: TradeOffer,
    inputs: EvaluationInputs,
    cpu_team_id: int
) -> EvaluationResult:
    """
    Evaluate a trade from the CPU's perspective.
    
    Args:
        sess: Database session
        offer: The trade offer to evaluate
        inputs: Calibration parameters
        cpu_team_id: The team ID representing the CPU
        
    Returns:
        EvaluationResult with decision and explanation
    """
    cpu_side = offer.to_side if offer.to_side.team_id == cpu_team_id else offer.from_side
    human_side = offer.from_side if offer.to_side.team_id == cpu_team_id else offer.to_side
    
    # Sum values for both sides
    cpu_value = _sum_assets_value(sess, cpu_side, offer, inputs)
    human_value = _sum_assets_value(sess, human_side, offer, inputs)
    
    # Calculate surpluses
    cpu_surplus = cpu_value - human_value
    human_surplus = human_value - cpu_value
    
    # Fairness score: ratio of CPU surplus to total
    total_value = cpu_value + human_value
    fairness = (cpu_value / total_value) if total_value > 0 else 0.5
    
    # Get team counts and cap after trade
    cpu_counts = _adapters.get_team_counts_after_simple(
        sess, cpu_team_id, 
        cpu_side.player_ids, 
        human_side.player_ids
    )
    
    cpu_cap = _adapters.get_cap_after_simple(
        sess, cpu_team_id,
        cpu_side.player_ids,
        human_side.player_ids,
        inputs.season_year
    )
    
    # Check hard vetoes
    veto = hard_veto_reason(
        offer, cpu_counts, cpu_cap, inputs
    )
    
    # Build explanation
    explanation = []
    explanation.append(f"CPU receives ${cpu_value:.1f} value, Human receives ${human_value:.1f} value")
    explanation.append(f"Fairness score: {fairness:.2f}")
    
    if veto:
        explanation.append(f"Hard veto: {veto}")
        return EvaluationResult(
            fairness=fairness,
            cpu_surplus=cpu_surplus,
            human_surplus=human_surplus,
            cpu_accepts=False,
            hard_veto=veto,
            explanation=explanation,
            need_gain={},
            counter_suggestion=None
        )
    
    # Check fairness thresholds
    if fairness < inputs.fairness_floor_cpu:
        explanation.append(f"Fairness {fairness:.2f} below threshold {inputs.fairness_floor_cpu}")
        return EvaluationResult(
            fairness=fairness,
            cpu_surplus=cpu_surplus,
            human_surplus=human_surplus,
            cpu_accepts=False,
            explanation=explanation,
            need_gain={},
            counter_suggestion=None
        )
    
    # Check negative surplus limit
    if cpu_surplus < inputs.max_negative_surplus:
        explanation.append(f"CPU deficit {cpu_surplus:.1f} exceeds limit {inputs.max_negative_surplus}")
        return EvaluationResult(
            fairness=fairness,
            cpu_surplus=cpu_surplus,
            human_surplus=human_surplus,
            cpu_accepts=False,
            explanation=explanation,
            need_gain={},
            counter_suggestion=None
        )
    
    # Check need improvement
    need_gain = _adapters.compute_need_gain_simple(sess, cpu_team_id, offer, inputs.season_year)
    meets_need_threshold = any(
        gain >= inputs.min_need_improvement for gain in need_gain.values()
    )
    
    if meets_need_threshold:
        explanation.append(f"Meets need improvement threshold: {need_gain}")
        return EvaluationResult(
            fairness=fairness,
            cpu_surplus=cpu_surplus,
            human_surplus=human_surplus,
            cpu_accepts=True,
            explanation=explanation,
            need_gain=need_gain,
            counter_suggestion=None
        )
    
    # Check if in counter band
    counter_band_low = 0.80
    counter_band_high = 0.92
    
    if counter_band_low <= fairness < counter_band_high:
        explanation.append(f"In counter band, suggesting adjustment")
        counter = _adapters.propose_counter_simple(cpu_team_id, offer, fairness, max_steps=3)
        return EvaluationResult(
            fairness=fairness,
            cpu_surplus=cpu_surplus,
            human_surplus=human_surplus,
            cpu_accepts=False,
            explanation=explanation,
            need_gain=need_gain,
            counter_suggestion=counter
        )
    
    # Default: reject
    explanation.append("Does not meet acceptance criteria")
    return EvaluationResult(
        fairness=fairness,
        cpu_surplus=cpu_surplus,
        human_surplus=human_surplus,
        cpu_accepts=False,
        explanation=explanation,
        need_gain=need_gain,
        counter_suggestion=None
    )


def _sum_assets_value(
    sess: Session,
    side: TradeSide,
    offer: TradeOffer,
    inputs: EvaluationInputs
) -> float:
    """Sum the value of all assets in a trade side."""
    total = 0.0
    
    # Process players
    for player_id in side.player_ids:
        info = _adapters.get_player_basic_info(sess, player_id)
        if not info:
            continue
        
        # Get team needs for need fit bonus
        team_needs = _adapters.get_team_needs_simple(
            sess, side.team_id, inputs.season_year
        )
        position = info.get('position', 'QB')
        team_need = team_needs.get(position, 0.0)
        
        # Calculate player value
        player_val = player_base_value(
            position=position,
            ovr=info.get('ovr', 50),
            potential=info.get('potential', 50),
            age=info.get('age', 25),
            contract_years=info.get('contract_years', 2),
            aav=info.get('contract_salary_aav', 0),
            inputs=inputs
        )
        
        # Apply need fit
        net_value = apply_need_fit(position, player_val.net_value, team_need, inputs)
        total += net_value
    
    # Process picks
    for pick_dict in side.picks:
        season = pick_dict.get('season', inputs.season_year)
        round_ = pick_dict.get('round', 1)
        
        pick_val = pick_value(season, round_, inputs.season_year, inputs)
        total += pick_val.net_value
    
    # Add cash value (simplified: 1M = 1 value point)
    total += side.cash / 1_000_000.0
    
    return total
