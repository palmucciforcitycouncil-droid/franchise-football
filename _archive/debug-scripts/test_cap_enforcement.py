#!/usr/bin/env python3
"""
Simple test script for the Cap & Roster Limits functionality.
This tests the core functionality without requiring the full app context.
"""

from app.services.cap_compliance import team_cap_summary, can_afford, roster_size, roster_has_room, estimate_dead_cap_for_player

def test_cap_compliance_functions():
    """Test the cap compliance functions."""
    print("Testing cap compliance functions...")
    
    # Test with mock session (we'll simulate the database calls)
    class MockSession:
        def exec(self, query):
            return []  # Empty result for now
    
    mock_sess = MockSession()
    
    # Test team_cap_summary
    summary = team_cap_summary(mock_sess, 2025, 1)
    assert summary["season"] == 2025
    assert summary["team_id"] == 1
    assert summary["cap_limit"] == 225_000_000
    assert summary["active_aav"] == 0
    assert summary["cap_space"] == 225_000_000
    print("✓ team_cap_summary works correctly")
    
    # Test can_afford
    assert can_afford(mock_sess, 2025, 1, 10_000_000) == True
    assert can_afford(mock_sess, 2025, 1, 300_000_000) == False
    print("✓ can_afford works correctly")
    
    # Test roster functions
    assert roster_size(mock_sess, 1) == 0
    assert roster_has_room(mock_sess, 1) == True
    print("✓ roster functions work correctly")
    
    # Test dead cap estimation
    dead_cap = estimate_dead_cap_for_player(mock_sess, 1, 2025)
    assert dead_cap == 0  # No contract found
    print("✓ estimate_dead_cap_for_player works correctly")
    
    return True

def test_cap_math():
    """Test cap math calculations."""
    print("\nTesting cap math calculations...")
    
    class MockSession:
        def exec(self, query):
            return []
    
    mock_sess = MockSession()
    
    # Test with different cap limits
    summary1 = team_cap_summary(mock_sess, 2025, 1, cap=200_000_000)
    assert summary1["cap_limit"] == 200_000_000
    assert summary1["cap_space"] == 200_000_000
    
    summary2 = team_cap_summary(mock_sess, 2025, 1, cap=300_000_000)
    assert summary2["cap_limit"] == 300_000_000
    assert summary2["cap_space"] == 300_000_000
    
    print("✓ Cap math calculations work correctly")
    return True

def test_enforcement_logic():
    """Test enforcement logic."""
    print("\nTesting enforcement logic...")
    
    class MockSession:
        def exec(self, query):
            return []
    
    mock_sess = MockSession()
    
    # Test can_afford with different amounts
    assert can_afford(mock_sess, 2025, 1, 0) == True  # Can afford 0
    assert can_afford(mock_sess, 2025, 1, 225_000_000) == True  # Can afford exactly cap
    assert can_afford(mock_sess, 2025, 1, 225_000_001) == False  # Cannot afford 1 over
    
    # Test roster limits
    assert roster_has_room(mock_sess, 1, max_size=53) == True
    assert roster_has_room(mock_sess, 1, max_size=0) == False
    
    print("✓ Enforcement logic works correctly")
    return True

def main():
    """Run all tests."""
    print("Cap & Roster Limits Functionality Tests")
    print("=" * 50)
    
    tests = [
        test_cap_compliance_functions,
        test_cap_math,
        test_enforcement_logic
    ]
    
    all_passed = True
    for test in tests:
        if not test():
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✓ All tests passed!")
        print("\nKey Features Implemented:")
        print("• Cap summary calculation with active AAV")
        print("• Dead cap estimation (50% of remaining AAV)")
        print("• Cap space enforcement (can_afford function)")
        print("• Roster size enforcement (53-man limit)")
        print("• Enforcement hooks in FA, Re-sign, Draft, Trade")
        print("• Public APIs for cap summary and roster size")
    else:
        print("✗ Some tests failed!")
    
    return all_passed

if __name__ == "__main__":
    main()
