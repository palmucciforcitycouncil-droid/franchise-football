# CPU Trade Evaluation - Implementation Status

## Overview
Implementation of a deterministic, explainable CPU trade evaluator to replace the naive "accept all" behavior.

## Current Status: PARTIAL IMPLEMENTATION

### ✅ Completed Components

1. **Schemas** (`app/services/trade/schemas.py`)
   - `TradeOffer`, `TradeSide`, `AssetValue`, `TeamNeeds`
   - `EvaluationInputs` with all calibration parameters
   - `EvaluationResult` with explanation trail

2. **Calibrations** (`app/services/trade/calibrations.py`)
   - Pick round base values (R1=42, R2=26, etc.)
   - Age decay curves (27 for non-QB, 30 for QB)
   - Position buckets and critical positions

3. **Rules** (`app/services/trade/rules.py`)
   - Hard veto logic for QB/K/P minimums
   - Cap space validation
   - Roster minimum enforcement

4. **Value Model** (`app/services/trade/value_model.py`)
   - `player_base_value()` - calculates player worth from OVR, age, contract
   - `pick_value()` - calculates pick worth with future year discount
   - `apply_need_fit()` - applies team need bonus

5. **Adapters** (`app/services/trade/_adapters.py`)
   - `get_player_basic_info()` - fetches player data for evaluation
   - `get_team_needs_simple()` - gets team needs (0-1 scale)
   - `get_team_counts_after_simple()` - calculates post-trade roster counts
   - `get_cap_after_simple()` - calculates post-trade cap space
   - `compute_need_gain_simple()` - placeholder for need improvement calc
   - `propose_counter_simple()` - placeholder for counter offer

### ⏳ Remaining Components

1. **Evaluator** (`app/services/trade/evaluator.py`) - NOT YET IMPLEMENTED
   - Main `evaluate_trade()` function
   - Fairness score calculation
   - Threshold gates (accept/counter/reject)
   - Counter offer generation

2. **API Endpoint** (`app/api/trade.py` or integration in `app/ui/api_trades.py`)
   - Simulate-only POST endpoint for preview
   - Integration with existing trade proposal flow

3. **Tests** (`tests/trade/`)
   - `test_value_model.py` - value calculation tests
   - `test_rules.py` - hard veto tests
   - `test_evaluator.py` - end-to-end evaluation tests

## Architecture

```
/app/services/trade/
├── __init__.py          ✅ Export main types
├── schemas.py           ✅ Pydantic models
├── calibrations.py      ✅ Constants
├── rules.py             ✅ Hard constraints
├── value_model.py       ✅ Pricing logic
├── _adapters.py         ✅ Bridge to existing services
└── evaluator.py         ⏳ Main evaluation logic (TODO)

/app/api/trade.py        ⏳ API endpoint (TODO)

/tests/trade/            ⏳ Test suite (TODO)
├── test_value_model.py
├── test_rules.py
└── test_evaluator.py
```

## Design Philosophy

1. **Determinism**: No RNG in acceptance decisions
2. **Explainability**: Decision trail in `EvaluationResult.explanation`
3. **Separability**: Pure functions for math, adapters for data access
4. **Error Handling**: Standard JSON error responses

## Key Features (Planned)

### Fairness Scoring
- Ratio-based fairness metric (cpu_surplus / total_surplus)
- Configurable threshold bands (accept: 0.92+, counter: 0.80-0.92)
- Negative surplus limits

### Need Improvement
- Position-specific need scoring
- Minimum improvement threshold (+6 position value)
- Trade must improve at least one priority need

### Hard Vetoes
- QB/K/P minimum enforcement (must have at least 2 QB, 1 K, 1 P)
- Cap space violations
- Roster minimum warnings (soft)

### Counter Offers
- Suggested delta (add/remove asset IDs)
- Within counter band fairness (0.80-0.92)
- Max steps to prevent infinite loops

## Integration Points

### With Existing Trade Engine
The CPU evaluation will integrate with `app/services/trade_engine.py`:
- Enhance `propose()` to use CPU evaluator instead of simple ratio
- Return `EvaluationResult` with explanation
- Support counter offer generation

### With Existing APIs
Add new endpoint or enhance existing:
- `POST /api/v1/trades/simulate` - preview CPU decision
- Enhance `POST /api/v1/trades/propose` - include evaluation

## Next Steps

1. Complete `evaluator.py` implementation
   - Wire adapters to main logic
   - Implement fairness calculation
   - Add threshold gates
   - Counter offer generation

2. Create API endpoint
   - Add `/simulate` endpoint
   - Integrate with existing proposal flow

3. Write tests
   - Value model tests
   - Rules tests  
   - End-to-end evaluator tests

4. Integrate with existing trade engine
   - Replace simple ratio check
   - Use evaluation result in `propose()`

## Notes

- Current implementation has basic structure but evaluator logic is incomplete
- Adapters are simplified; may need enhancement based on actual data models
- Some placeholder logic needs refinement (cap calculation, need improvement)
- Test coverage target: >85% for `/services/trade` module
