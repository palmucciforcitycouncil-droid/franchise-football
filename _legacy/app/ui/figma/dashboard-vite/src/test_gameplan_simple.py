import pytest
from app.models.gameplan import OffAgg, DefAgg, Coverage, BlitzStrategy, RZOff, RZDef
from app.services.gameplan_mapping import build_deltas

def test_basic_gameplan_functionality():
    """Test basic gameplan functionality."""
    # Test that aggressive offense has positive deltas
    d = build_deltas(OffAgg.VERY_AGGRESSIVE, DefAgg.BALANCED, Coverage.HYBRID, 
                     BlitzStrategy.STANDARD, RZOff.BALANCED, RZDef.BALANCED)
    
    assert d.pass_bias_delta > 0
    assert d.depth_bias_delta > 0
    assert d.go4it_cutoff_delta < 0
    assert d.two_point_tendency_delta > 0
    
    # Test that blitz heavy multiplies correctly
    d2 = build_deltas(OffAgg.BALANCED, DefAgg.BALANCED, Coverage.HYBRID, 
                      BlitzStrategy.BLITZ_HEAVY, RZOff.BALANCED, RZDef.BALANCED)
    
    assert abs(d2.blitz_rate_multiplier - 1.20) < 1e-9
    assert d2.explosive_play_risk_weight > 0
    
    print("✅ Basic gameplan functionality test passed!")

if __name__ == "__main__":
    test_basic_gameplan_functionality()

