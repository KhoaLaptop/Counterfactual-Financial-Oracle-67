"""
Unit tests for financial formulas.
"""

import pytest
import numpy as np
from src.financial_formulas import (
    calculate_ebitda,
    calculate_ebit,
    calculate_net_income,
    calculate_free_cash_flow,
    calculate_npv,
    apply_delta_percentage,
    calculate_percentiles,
    monte_carlo_simulation
)


class TestFinancialFormulas:
    """Test financial formula calculations."""
    
    def test_calculate_ebitda(self):
        """Test EBITDA calculation."""
        revenue = 1000000
        opex = 300000
        cogs = 200000
        
        ebitda = calculate_ebitda(revenue, opex, cogs)
        expected = revenue - cogs - opex
        assert ebitda == expected
        assert ebitda == 500000
    
    def test_calculate_ebit(self):
        """Test EBIT calculation."""
        ebitda = 500000
        depreciation = 50000
        amortization = 10000
        
        ebit = calculate_ebit(ebitda, depreciation, amortization)
        expected = ebitda - depreciation - amortization
        assert ebit == expected
        assert ebit == 440000
    
    def test_calculate_net_income(self):
        """Test net income calculation."""
        ebit = 440000
        interest_expense = 20000
        tax_rate = 0.25
        other_income = 0
        
        net_income = calculate_net_income(ebit, interest_expense, tax_rate, other_income)
        ebt = ebit - interest_expense + other_income
        expected = ebt * (1 - tax_rate)
        assert net_income == expected
        assert net_income == 315000
    
    def test_calculate_free_cash_flow(self):
        """Test free cash flow calculation."""
        net_income = 315000
        depreciation = 50000
        amortization = 10000
        capex = 100000
        working_capital_delta = 20000
        other_adjustments = 0
        
        fcf = calculate_free_cash_flow(
            net_income, depreciation, amortization, capex, working_capital_delta, other_adjustments
        )
        expected = net_income + depreciation + amortization - capex - working_capital_delta
        assert fcf == expected
        assert fcf == 255000
    
    def test_calculate_npv(self):
        """Test NPV calculation."""
        cash_flows = [100000, 110000, 121000, 133100, 146410]
        discount_rate = 0.10
        initial_investment = 0
        
        npv = calculate_npv(cash_flows, discount_rate, initial_investment)
        
        # Manual calculation
        expected = (
            100000 / (1.10 ** 1) +
            110000 / (1.10 ** 2) +
            121000 / (1.10 ** 3) +
            133100 / (1.10 ** 4) +
            146410 / (1.10 ** 5)
        )
        assert abs(npv - expected) < 0.01
    
    def test_apply_delta_percentage(self):
        """Test applying delta in basis points."""
        value = 1000000
        delta_bps = -50  # -50 bps = -0.5%
        
        adjusted = apply_delta_percentage(value, delta_bps)
        expected = value * (1 - 0.005)
        assert adjusted == expected
        assert adjusted == 995000
    
    def test_calculate_percentiles(self):
        """Test percentile calculation."""
        values = list(range(1, 101))  # 1 to 100
        percentiles = calculate_percentiles(values, [10, 50, 90])
        
        assert abs(percentiles[10] - 10) < 1
        assert abs(percentiles[50] - 50) < 1
        assert abs(percentiles[90] - 90) < 1
    
    def test_monte_carlo_simulation(self):
        """Test Monte Carlo simulation."""
        base_value = 1000000
        num_scenarios = 1000
        mean_delta = 0.0
        std_delta = 0.01
        
        scenarios = monte_carlo_simulation(
            base_value, num_scenarios, mean_delta, std_delta, "normal"
        )
        
        assert len(scenarios) == num_scenarios
        assert all(isinstance(s, (int, float)) for s in scenarios)
        
        # Check that most values are within reasonable range
        mean_scenario = np.mean(scenarios)
        assert abs(mean_scenario - base_value) < base_value * 0.1


if __name__ == "__main__":
    pytest.main([__file__])

