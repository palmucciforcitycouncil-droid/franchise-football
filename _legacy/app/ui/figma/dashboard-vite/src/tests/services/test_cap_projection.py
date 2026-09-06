import pytest
import math
from app.services.cap import nearest_5_floor, project_cap_for_year, get_current_league_cap, get_growth_rate

class TestNearest5Floor:
    """Test the nearest_5_floor function for various inputs."""
    
    def test_exact_multiples_of_5(self):
        """Test that exact multiples of 5 remain unchanged."""
        assert nearest_5_floor(255) == 255
        assert nearest_5_floor(260) == 260
        assert nearest_5_floor(265) == 265
        assert nearest_5_floor(0) == 0
    
    def test_round_down_to_5(self):
        """Test that values are rounded down to nearest multiple of 5."""
        assert nearest_5_floor(259) == 255
        assert nearest_5_floor(261) == 260
        assert nearest_5_floor(264) == 260
        assert nearest_5_floor(266) == 265
        assert nearest_5_floor(269) == 265
    
    def test_negative_values(self):
        """Test negative values (should round down, making them more negative)."""
        assert nearest_5_floor(-1) == -5
        assert nearest_5_floor(-3) == -5
        assert nearest_5_floor(-4) == -5
        assert nearest_5_floor(-6) == -10
    
    def test_float_inputs(self):
        """Test that float inputs are handled correctly."""
        assert nearest_5_floor(259.9) == 255
        assert nearest_5_floor(260.1) == 260
        assert nearest_5_floor(264.9) == 260

class TestProjectCapForYear:
    """Test the project_cap_for_year function."""
    
    def test_same_year(self):
        """Test that projecting to the same year returns the base cap."""
        result = project_cap_for_year(2025, 2025, 255_000_000, 5.0)
        assert result == 255_000_000
    
    def test_past_year(self):
        """Test that projecting to a past year returns the base cap."""
        result = project_cap_for_year(2025, 2024, 255_000_000, 5.0)
        assert result == 255_000_000
    
    def test_one_year_growth(self):
        """Test 5% growth over one year."""
        # 255M * 1.05 = 267.75M -> floor to 5 = 267.75M -> nearest_5_floor = 265M
        result = project_cap_for_year(2025, 2026, 255_000_000, 5.0)
        expected = nearest_5_floor(255_000_000 * 1.05)
        assert result == expected
        assert result == 265_000_000
    
    def test_two_year_growth(self):
        """Test 5% growth over two years."""
        # 255M * (1.05)^2 = 255M * 1.1025 = 281.1375M -> nearest_5_floor = 280M
        result = project_cap_for_year(2025, 2027, 255_000_000, 5.0)
        expected = nearest_5_floor(255_000_000 * (1.05 ** 2))
        assert result == expected
        assert result == 280_000_000
    
    def test_three_year_growth(self):
        """Test 5% growth over three years."""
        # 255M * (1.05)^3 = 255M * 1.157625 = 295.194375M -> nearest_5_floor = 295M
        result = project_cap_for_year(2025, 2028, 255_000_000, 5.0)
        expected = nearest_5_floor(255_000_000 * (1.05 ** 3))
        assert result == expected
        assert result == 295_000_000
    
    def test_different_growth_rate(self):
        """Test with different growth rate."""
        # 255M * (1.03)^2 = 255M * 1.0609 = 270.5295M -> nearest_5_floor = 270M
        result = project_cap_for_year(2025, 2027, 255_000_000, 3.0)
        expected = nearest_5_floor(255_000_000 * (1.03 ** 2))
        assert result == expected
        assert result == 270_000_000
    
    def test_zero_growth_rate(self):
        """Test with zero growth rate."""
        result = project_cap_for_year(2025, 2028, 255_000_000, 0.0)
        assert result == 255_000_000
    
    def test_rounding_consistency(self):
        """Test that rounding is applied consistently."""
        # Test a case where the exact calculation would be 260.5M
        # This should round down to 260M
        base_cap = 248_095_238  # This gives exactly 260.5M after 5% growth
        result = project_cap_for_year(2025, 2026, base_cap, 5.0)
        assert result == 260_000_000

class TestCapProjectionIntegration:
    """Test cap projection with realistic scenarios."""
    
    def test_league_cap_progression(self):
        """Test a realistic league cap progression over multiple years."""
        base_cap = 255_000_000
        growth_rate = 5.0
        
        # Test progression from 2025 to 2030
        years = [2025, 2026, 2027, 2028, 2029, 2030]
        results = []
        
        for year in years:
            projected = project_cap_for_year(2025, year, base_cap, growth_rate)
            results.append(projected)
        
        # Verify that each year is higher than the previous (or equal)
        for i in range(1, len(results)):
            assert results[i] >= results[i-1], f"Year {years[i]} cap should be >= year {years[i-1]} cap"
        
        # Verify all results are multiples of 5
        for result in results:
            assert result % 5 == 0, f"Result {result} should be a multiple of 5"
    
    def test_growth_consistency(self):
        """Test that growth calculations are consistent with manual calculations."""
        base_cap = 255_000_000
        growth_rate = 5.0
        
        # Manual calculation for 3 years
        manual_calc = base_cap * (1.05 ** 3)
        manual_rounded = nearest_5_floor(manual_calc)
        
        # Function calculation
        function_result = project_cap_for_year(2025, 2028, base_cap, growth_rate)
        
        assert function_result == manual_rounded
        assert function_result == 295_000_000
