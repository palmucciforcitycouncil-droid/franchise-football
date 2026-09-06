#!/usr/bin/env python3
"""
Simple test script for the GM Salary Cap functionality.
This tests the core functionality without requiring the full app context.
"""

from app.services.cap import nearest_5_floor, project_cap_for_year

def test_nearest_5_floor():
    """Test the nearest_5_floor function."""
    print("Testing nearest_5_floor function...")
    
    test_cases = [
        (259, 255),
        (260, 260),
        (261, 260),
        (264, 260),
        (265, 265),
        (0, 0),
        (-1, -5),
        (-3, -5),
        (-6, -10)
    ]
    
    all_passed = True
    for input_val, expected in test_cases:
        result = nearest_5_floor(input_val)
        if result == expected:
            print(f"✓ nearest_5_floor({input_val}) = {result}")
        else:
            print(f"✗ nearest_5_floor({input_val}) = {result}, expected {expected}")
            all_passed = False
    
    return all_passed

def test_project_cap_for_year():
    """Test the project_cap_for_year function."""
    print("\nTesting project_cap_for_year function...")
    
    base_cap = 255_000_000
    growth_rate = 5.0
    
    test_cases = [
        (2025, 2025, base_cap),  # Same year
        (2025, 2026, 267_750_000),  # One year growth
        (2025, 2027, 281_137_500),  # Two year growth
        (2025, 2028, 295_194_375),  # Three year growth
    ]
    
    all_passed = True
    for base_year, target_year, expected in test_cases:
        result = project_cap_for_year(base_year, target_year, base_cap, growth_rate)
        if result == expected:
            print(f"✓ project_cap_for_year({base_year}, {target_year}) = {result}")
        else:
            print(f"✗ project_cap_for_year({base_year}, {target_year}) = {result}, expected {expected}")
            all_passed = False
        
        # Verify result is multiple of 5
        if result % 5 == 0:
            print(f"  ✓ Result is multiple of 5")
        else:
            print(f"  ✗ Result is NOT multiple of 5")
            all_passed = False
    
    return all_passed

def test_cap_progression():
    """Test realistic cap progression over multiple years."""
    print("\nTesting cap progression over multiple years...")
    
    base_cap = 255_000_000
    growth_rate = 5.0
    
    years = [2025, 2026, 2027, 2028, 2029, 2030]
    results = []
    
    for year in years:
        projected = project_cap_for_year(2025, year, base_cap, growth_rate)
        results.append(projected)
        print(f"  {year}: ${projected:,}")
    
    # Verify progression
    all_passed = True
    for i in range(1, len(results)):
        if results[i] >= results[i-1]:
            print(f"  ✓ {years[i]} cap >= {years[i-1]} cap")
        else:
            print(f"  ✗ {years[i]} cap < {years[i-1]} cap")
            all_passed = False
    
    # Verify all are multiples of 5
    for i, result in enumerate(results):
        if result % 5 == 0:
            print(f"  ✓ {years[i]} cap is multiple of 5")
        else:
            print(f"  ✗ {years[i]} cap is NOT multiple of 5")
            all_passed = False
    
    return all_passed

def main():
    """Run all tests."""
    print("GM Salary Cap Functionality Tests")
    print("=" * 40)
    
    tests = [
        test_nearest_5_floor,
        test_project_cap_for_year,
        test_cap_progression
    ]
    
    all_passed = True
    for test in tests:
        if not test():
            all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed!")
    
    return all_passed

if __name__ == "__main__":
    main()
