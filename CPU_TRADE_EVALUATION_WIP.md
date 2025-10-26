# CPU Trade Evaluation - Implementation Status

## Overview
Implementation of a deterministic, explainable CPU trade evaluator to replace the naive "accept all" behavior.

## Current Status: CORE COMPLETE, TESTS PENDING

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

6. **Evaluator** (`app/services/trade/evaluator.py`) ✅
   - `evaluate_trade()` - main evaluation logic
   - Fairness score calculation (ratio-based)
   - Threshold gates (accept ≥0.92, counter 0.80-0.92, reject <0.80)
   - Hard veto checks (QB/K/P minimums, cap violations)
   - Need improvement analysis (must improve by ≥6 position value)
   - Counter offer generation logic

7. **API Endpoint** (`app/ui/api_trades.py`) ✅
   - `POST /api/v1/trades/simulate` - preview CPU decision
   - Returns evaluation result with explanation trail
   - Integrated with existing trade proposal flow

### ⏳ Remaining Components

1. **Tests** (`tests/trade/`)
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
└── evaluator.py         ✅ Main evaluation logic

/app/ui/api_trades.py    ✅ API endpoint (simulate)

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

## Key Features (Implemented)

### Fairness Scoring
- Ratio-based fairness metric (cpu_value / total_value)
- Configurable threshold bands (accept: 0.92+, counter: 0.80-0.92)
- Negative surplus limits (default: -15 value points)

### Need Improvement
- Position-specific need scoring via team needs service
- Minimum improvement threshold (+6 position value)
- Trade must improve at least one priority need to accept

### Hard Vetoes
- QB/K/P minimum enforcement (must have at least 2 QB, 1 K, 1 P)
- Cap space violations (cap_space < 0)
- Roster minimum warnings (soft)

### Counter Offers
- Suggested delta (add/remove asset IDs)
- Within counter band fairness (0.80-0.92)
- Max steps to prevent infinite loops

## Integration Points

### With Existing Trade Engine
The CPU evaluation integrates with `app/services/trade_engine.py`:
- Can be called before creating a proposal to preview decision
- Returns `EvaluationResult` with explanation
- Supports counter offer generation

### With Existing APIs
New endpoint added:
- `POST /api/v1/trades/simulate` - preview CPU decision
- Uses same request format as `POST /api/v1/trades/propose`
- Returns evaluation result with explanation trail

## Next Steps

1. Write tests ⏳
   - Value model tests
   - Rules tests  
   - End-to-end evaluator tests
   - Target: >85% coverage for `/services/trade` module

2. Integration testing
   - Test with real team data
   - Validate fairness calculations
   - Verify hard vetoes work correctly

3. Fine-tune calibrations
   - Adjust fairness thresholds based on testing
   - Calibrate pick values vs player values
   - Tune age decay curves

## Notes

- Core evaluation logic is complete and functional
- API endpoint ready for frontend integration
- Adapters use simplified logic; may need enhancement based on actual data models
- Some placeholder logic (cap calculation, need improvement) uses fallbacks
- Test coverage target: >85% for `/services/trade` module
