"""
Edge case tests for financial formulas and simulation engine.
"""

import pytest
import math
import numpy as np
from src.financial_formulas import (
    calculate_ebitda,
    calculate_ebit,
    calculate_net_income,
    calculate_free_cash_flow,
    calculate_npv,
    apply_delta_percentage,
    monte_carlo_simulation
)
from src.balance_sheet_checker import (
    check_balance_sheet_balance,
    check_cash_flow_consistency,
    validate_financial_ratios,
    check_historical_ranges
)


class TestFinancialFormulasEdgeCases:
    """Test edge cases for financial formulas."""
    
    def test_negative_revenue(self):
        """Test handling of negative revenue."""
        revenue = -1000000
        opex = 300000
        cogs = 200000
        
        ebitda = calculate_ebitda(revenue, opex, cogs)
        # Negative revenue should result in negative EBITDA
        assert ebitda == -1500000
    
    def test_negative_ebitda(self):
        """Test negative EBITDA (loss scenario)."""
        revenue = 1000000
        opex = 1500000  # OpEx exceeds revenue
        cogs = 200000
        
        ebitda = calculate_ebitda(revenue, opex, cogs)
        assert ebitda == -700000
    
    def test_zero_revenue(self):
        """Test zero revenue."""
        revenue = 0
        opex = 300000
        cogs = 200000
        
        ebitda = calculate_ebitda(revenue, opex, cogs)
        assert ebitda == -500000
    
    def test_zero_opex(self):
        """Test zero operating expenses."""
        revenue = 1000000
        opex = 0
        cogs = 200000
        
        ebitda = calculate_ebitda(revenue, opex, cogs)
        assert ebitda == 800000
    
    def test_negative_npv(self):
        """Test negative NPV."""
        cash_flows = [-1000000, 200000, 200000, 200000]  # Initial investment > returns
        discount_rate = 0.10
        
        npv = calculate_npv(cash_flows, discount_rate)
        assert npv < 0
    
    def test_zero_discount_rate(self):
        """Test NPV with zero discount rate."""
        cash_flows = [100000, 110000, 121000]
        discount_rate = 0.0
        
        npv = calculate_npv(cash_flows, discount_rate)
        # With zero discount rate, NPV is just sum of cash flows
        expected = sum(cash_flows)
        assert abs(npv - expected) < 0.01
    
    def test_very_high_discount_rate(self):
        """Test NPV with very high discount rate."""
        cash_flows = [100000, 110000, 121000]
        discount_rate = 0.50  # 50%
        
        npv = calculate_npv(cash_flows, discount_rate)
        # High discount rate should significantly reduce NPV
        assert npv < sum(cash_flows)
    
    def test_negative_cash_flows(self):
        """Test NPV with negative cash flows."""
        cash_flows = [100000, -50000, 150000]
        discount_rate = 0.10
        
        npv = calculate_npv(cash_flows, discount_rate)
        # Should handle negative cash flows
        assert isinstance(npv, (int, float))
    
    def test_extreme_delta_percentage(self):
        """Test very large delta in basis points."""
        value = 1000000
        delta_bps = 5000  # 50% change
        
        adjusted = apply_delta_percentage(value, delta_bps)
        assert adjusted == 1500000
    
    def test_negative_delta_percentage(self):
        """Test negative delta in basis points."""
        value = 1000000
        delta_bps = -5000  # -50% change
        
        adjusted = apply_delta_percentage(value, delta_bps)
        assert adjusted == 500000
    
    def test_extreme_delta_percentage(self):
        """Test extreme delta (>100% change)."""
        value = 1000000
        delta_bps = 20000  # 200% change
        
        adjusted = apply_delta_percentage(value, delta_bps)
        assert adjusted == 3000000
    
    def test_net_income_with_negative_ebit(self):
        """Test net income calculation with negative EBIT."""
        ebit = -100000
        interest_expense = 20000
        tax_rate = 0.25
        other_income = 0
        
        net_income = calculate_net_income(ebit, interest_expense, tax_rate, other_income)
        # Negative EBIT should result in negative net income
        assert net_income < 0
    
    def test_net_income_zero_tax_rate(self):
        """Test net income with zero tax rate."""
        ebit = 1000000
        interest_expense = 20000
        tax_rate = 0.0
        other_income = 0
        
        net_income = calculate_net_income(ebit, interest_expense, tax_rate, other_income)
        # With zero tax, net income = EBIT - Interest
        assert net_income == 980000
    
    def test_net_income_invalid_tax_rate(self):
        """Test net income with invalid tax rate (>1)."""
        ebit = 1000000
        interest_expense = 20000
        tax_rate = 1.5  # 150% - invalid but function will still calculate
        other_income = 0
        
        net_income = calculate_net_income(ebit, interest_expense, tax_rate, other_income)
        # Should handle invalid tax rate (result will be negative)
        assert isinstance(net_income, (int, float))
    
    def test_free_cash_flow_negative(self):
        """Test negative free cash flow."""
        net_income = 100000
        depreciation = 50000
        amortization = 10000
        capex = 200000  # High CapEx
        
        fcf = calculate_free_cash_flow(net_income, depreciation, amortization, capex)
        assert fcf < 0
    
    def test_monte_carlo_negative_base_value(self):
        """Test Monte Carlo with negative base value."""
        base_value = -1000000
        num_scenarios = 100
        
        scenarios = monte_carlo_simulation(base_value, num_scenarios, 0.0, 0.01)
        assert len(scenarios) == num_scenarios
        # Some scenarios might be positive or negative
        assert all(isinstance(s, (int, float)) for s in scenarios)
    
    def test_monte_carlo_zero_base_value(self):
        """Test Monte Carlo with zero base value."""
        base_value = 0
        num_scenarios = 100
        
        scenarios = monte_carlo_simulation(base_value, num_scenarios, 0.0, 0.01)
        assert len(scenarios) == num_scenarios
        # All scenarios should be close to zero
        assert all(abs(s) < 1.0 for s in scenarios)


class TestBalanceSheetEdgeCases:
    """Test edge cases for balance sheet checker."""
    
    def test_all_zero_balance_sheet(self):
        """Test balance sheet with all zeros."""
        assets = {"cash": 0, "inventory": 0}
        liabilities = {"debt": 0}
        equity = {"equity": 0}
        
        is_balanced, error, imbalance = check_balance_sheet_balance(assets, liabilities, equity)
        assert is_balanced is True
    
    def test_negative_equity(self):
        """Test balance sheet with negative equity."""
        assets = {"cash": 100000}
        liabilities = {"debt": 150000}
        equity = {"equity": -50000}  # Negative equity
        
        is_balanced, error, imbalance = check_balance_sheet_balance(assets, liabilities, equity)
        # Should still balance mathematically
        assert is_balanced is True
    
    def test_extreme_imbalance(self):
        """Test balance sheet with extreme imbalance."""
        assets = {"cash": 1000000}
        liabilities = {"debt": 100000}
        equity = {"equity": 100000}
        # Imbalance: 1000000 - 200000 = 800000 (80% of assets)
        
        is_balanced, error, imbalance = check_balance_sheet_balance(assets, liabilities, equity, tolerance=0.01)
        assert is_balanced is False
        assert imbalance > 0
    
    def test_empty_balance_sheet(self):
        """Test balance sheet with empty dictionaries."""
        assets = {}
        liabilities = {}
        equity = {}
        
        is_balanced, error, imbalance = check_balance_sheet_balance(assets, liabilities, equity)
        assert is_balanced is True
    
    def test_cash_flow_zero_values(self):
        """Test cash flow consistency with all zeros."""
        net_income = 0
        cash_from_ops = 0
        depreciation = 0
        amortization = 0
        working_capital_changes = 0
        
        is_consistent, error, difference = check_cash_flow_consistency(
            net_income, cash_from_ops, depreciation, amortization, working_capital_changes
        )
        assert is_consistent is True
    
    def test_financial_ratios_zero_revenue(self):
        """Test financial ratio validation with zero revenue."""
        revenue = 0
        ebitda = 500000
        net_income = 300000
        total_assets = 2000000
        
        results = validate_financial_ratios(revenue, ebitda, net_income, total_assets)
        # Should return empty results for zero revenue
        assert len(results) == 0
    
    def test_financial_ratios_zero_assets(self):
        """Test financial ratio validation with zero assets."""
        revenue = 1000000
        ebitda = 500000
        net_income = 300000
        total_assets = 0
        
        results = validate_financial_ratios(revenue, ebitda, net_income, total_assets)
        # ROA will be calculated but might be invalid
        assert isinstance(results, list)
    
    def test_historical_ranges_empty(self):
        """Test historical range check with empty history."""
        current_value = 1000000
        historical_values = []
        
        is_within, message = check_historical_ranges(current_value, historical_values, "revenue")
        assert is_within is True
        assert "No historical data" in message
    
    def test_historical_ranges_single_value(self):
        """Test historical range check with single historical value."""
        current_value = 1000000
        historical_values = [950000]
        
        is_within, message = check_historical_ranges(
            current_value, historical_values, "revenue", tolerance_percentage=0.20
        )
        # Should be within range with tolerance
        assert isinstance(is_within, bool)
    
    def test_historical_ranges_extreme_deviation(self):
        """Test historical range check with extreme deviation."""
        current_value = 10000000  # 10x historical
        historical_values = [950000, 980000, 1020000, 1050000, 990000]
        
        is_within, message = check_historical_ranges(
            current_value, historical_values, "revenue", tolerance_percentage=0.20
        )
        assert is_within is False
        assert "outside" in message.lower() or "deviation" in message.lower()


class TestSimulationEdgeCases:
    """Test edge cases for simulation inputs."""
    
    def test_extreme_user_controls(self):
        """Test simulation with extreme user controls."""
        from src.validators import validate_user_controls
        
        # Very large deltas
        user_controls = {
            "opex_delta_bps": 5000,  # 50% change
            "revenue_delta_bps": -3000,  # -30% change
            "discount_rate_base": 0.15,  # 15%
            "discount_rate_delta_bps": -500  # -5%
        }
        
        is_valid, warnings = validate_user_controls(user_controls)
        # Should generate warnings for extreme values
        assert len(warnings) > 0
    
    def test_negative_discount_rate(self):
        """Test user controls with negative discount rate."""
        from src.validators import validate_user_controls
        
        user_controls = {
            "opex_delta_bps": 0,
            "revenue_delta_bps": 0,
            "discount_rate_base": 0.08,
            "discount_rate_delta_bps": -10000  # Would make rate negative
        }
        
        is_valid, warnings = validate_user_controls(user_controls)
        # Should warn about negative discount rate
        assert any("negative" in w.lower() for w in warnings)
    
    def test_discount_rate_over_100_percent(self):
        """Test user controls with discount rate > 100%."""
        from src.validators import validate_user_controls
        
        user_controls = {
            "opex_delta_bps": 0,
            "revenue_delta_bps": 0,
            "discount_rate_base": 1.5,  # 150%
            "discount_rate_delta_bps": 0
        }
        
        is_valid, warnings = validate_user_controls(user_controls)
        # Should warn about discount rate > 100%
        assert any("100%" in w for w in warnings)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

