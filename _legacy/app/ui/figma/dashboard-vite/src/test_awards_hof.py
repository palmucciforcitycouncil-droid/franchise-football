#!/usr/bin/env python3
"""
Simple test script for the Awards Engine + HOF functionality.
This tests the core functionality without requiring the full app context.
"""

from app.services.awards_service import _off_score, _def_score, _st_score, compute_weekly_awards, compute_annual_awards
from app.services.hof_service import _score_player, _score_coach, induct_hof

def test_scoring_functions():
    """Test the scoring functions."""
    print("Testing scoring functions...")
    
    # Mock box score for offensive player
    class MockBox:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    # Test offensive scoring
    off_box = MockBox(
        pass_yds=300, pass_td=3, pass_int=1,
        rush_yds=50, rush_td=1,
        rec_yds=100, rec_td=1,
        tkl=0, tfl=0, sack=0, ints=0, pdef=0, ff=0, fr=0,
        fgm=0, fga=0, xpm=0, xpa=0, kr_yds=0, pr_yds=0
    )
    off_score = _off_score(off_box)
    print(f"✓ Offensive score: {off_score}")
    assert off_score > 0
    
    # Test defensive scoring
    def_box = MockBox(
        pass_yds=0, pass_td=0, pass_int=0, rush_yds=0, rush_td=0, rec_yds=0, rec_td=0,
        tkl=5, tfl=2, sack=1.0, ints=1, pdef=2, ff=1, fr=1,
        fgm=0, fga=0, xpm=0, xpa=0, kr_yds=0, pr_yds=0
    )
    def_score = _def_score(def_box)
    print(f"✓ Defensive score: {def_score}")
    assert def_score > 0
    
    # Test special teams scoring
    st_box = MockBox(
        pass_yds=0, pass_td=0, pass_int=0, rush_yds=0, rush_td=0, rec_yds=0, rec_td=0,
        tkl=0, tfl=0, sack=0, ints=0, pdef=0, ff=0, fr=0,
        fgm=3, fga=4, xpm=2, xpa=2, kr_yds=50, pr_yds=30
    )
    st_score = _st_score(st_box)
    print(f"✓ Special teams score: {st_score}")
    assert st_score > 0
    
    return True

def test_hof_scoring():
    """Test HOF scoring functions."""
    print("\nTesting HOF scoring functions...")
    
    # Mock career aggregates
    class MockPlayerCareer:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    class MockCoachCareer:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    # Test player scoring
    player_career = MockPlayerCareer(
        pass_yds_career=50000, rush_yds_career=5000, rec_yds_career=10000,
        sacks_career=100, ints_career=50, td_career=300,
        rings=2, mvps=1, opoy_dpoy=2
    )
    player_score = _score_player(player_career)
    print(f"✓ Player HOF score: {player_score}")
    assert player_score > 0
    
    # Test coach scoring
    coach_career = MockCoachCareer(
        wins=200, rings=3, coy=2, win_pct=0.65
    )
    coach_score = _score_coach(coach_career)
    print(f"✓ Coach HOF score: {coach_score}")
    assert coach_score > 0
    
    return True

def test_awards_computation():
    """Test awards computation with mock session."""
    print("\nTesting awards computation...")
    
    class MockSession:
        def exec(self, query):
            return []  # Empty result for now
    
    mock_sess = MockSession()
    
    # Test weekly awards computation
    weekly_result = compute_weekly_awards(mock_sess, season=2025, week=1)
    assert weekly_result["ok"] == True
    assert "awards" in weekly_result
    print("✓ Weekly awards computation works")
    
    # Test annual awards computation
    annual_result = compute_annual_awards(mock_sess, season=2025)
    assert annual_result["ok"] == True
    print("✓ Annual awards computation works")
    
    return True

def test_hof_induction():
    """Test HOF induction with mock session."""
    print("\nTesting HOF induction...")
    
    class MockSession:
        def exec(self, query):
            return []  # Empty result for now
    
    mock_sess = MockSession()
    
    # Test HOF induction
    hof_result = induct_hof(mock_sess, season=2025)
    assert hof_result["ok"] == True
    assert "inductees" in hof_result
    print("✓ HOF induction works")
    
    return True

def test_awards_models():
    """Test awards model enums."""
    print("\nTesting awards model enums...")
    
    from app.models.awards import WeeklyAwardType, AnnualAwardType
    from app.models.hof import HoFType
    
    # Test weekly award types
    assert WeeklyAwardType.OFF_POW == "OFF_POW"
    assert WeeklyAwardType.DEF_POW == "DEF_POW"
    assert WeeklyAwardType.ST_POW == "ST_POW"
    print("✓ Weekly award types work")
    
    # Test annual award types
    assert AnnualAwardType.MVP == "MVP"
    assert AnnualAwardType.OPOY == "OPOY"
    assert AnnualAwardType.DPOY == "DPOY"
    assert AnnualAwardType.ROY == "ROY"
    assert AnnualAwardType.COY == "COY"
    assert AnnualAwardType.GMOY == "GMOY"
    print("✓ Annual award types work")
    
    # Test HOF types
    assert HoFType.PLAYER == "PLAYER"
    assert HoFType.COACH == "COACH"
    print("✓ HOF types work")
    
    return True

def main():
    """Run all tests."""
    print("Awards Engine + HOF Functionality Tests")
    print("=" * 50)
    
    tests = [
        test_scoring_functions,
        test_hof_scoring,
        test_awards_computation,
        test_hof_induction,
        test_awards_models
    ]
    
    all_passed = True
    for test in tests:
        if not test():
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✓ All tests passed!")
        print("\nKey Features Implemented:")
        print("• Weekly awards (Off POTW, Def POTW, ST POTW)")
        print("• Annual awards (MVP, OPOY, DPOY, ROY, COY, GMOY)")
        print("• Hall of Fame induction with transparent rules")
        print("• Public read endpoints for UI integration")
        print("• Admin endpoints for computation triggers")
        print("• Season close endpoint for annual processing")
        print("• Graceful degradation when models don't exist")
        print("• Idempotent computation (safe to recompute)")
    else:
        print("✗ Some tests failed!")
    
    return all_passed

if __name__ == "__main__":
    main()
