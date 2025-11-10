"""
Unit tests for balance sheet checker.
"""

import pytest
from src.balance_sheet_checker import (
    check_balance_sheet_balance,
    check_cash_flow_consistency,
    validate_financial_ratios,
    check_historical_ranges
)


class TestBalanceSheetChecker:
    """Test balance sheet constraint checking."""
    
    def test_balanced_sheet(self):
        """Test balanced balance sheet."""
        assets = {"cash": 100000, "inventory": 200000, "pp_e": 500000}
        liabilities = {"accounts_payable": 150000, "long_term_debt": 400000}
        equity = {"common_stock": 100000, "retained_earnings": 150000}
        
        is_balanced, error, imbalance = check_balance_sheet_balance(assets, liabilities, equity)
        
        assert is_balanced is True
        assert error is None
        assert abs(imbalance) < 0.01
    
    def test_imbalanced_sheet(self):
        """Test imbalanced balance sheet."""
        assets = {"cash": 100000, "inventory": 200000, "pp_e": 500000}
        liabilities = {"accounts_payable": 150000, "long_term_debt": 400000}
        equity = {"common_stock": 100000, "retained_earnings": 100000}  # Wrong amount
        
        is_balanced, error, imbalance = check_balance_sheet_balance(assets, liabilities, equity)
        
        assert is_balanced is False
        assert error is not None
        assert imbalance > 0
    
    def test_cash_flow_consistency(self):
        """Test consistent cash flow."""
        net_income = 315000
        cash_from_ops = 375000
        depreciation = 50000
        amortization = 10000
        working_capital_changes = 0
        
        is_consistent, error, difference = check_cash_flow_consistency(
            net_income, cash_from_ops, depreciation, amortization, working_capital_changes
        )
        
        # Calculated CFO = 315000 + 50000 + 10000 = 375000
        assert is_consistent is True
        assert error is None
        assert abs(difference) < 1.0
    
    def test_cash_flow_inconsistency(self):
        """Test inconsistent cash flow."""
        net_income = 315000
        cash_from_ops = 400000  # Reported incorrectly
        depreciation = 50000
        amortization = 10000
        working_capital_changes = 0
        
        is_consistent, error, difference = check_cash_flow_consistency(
            net_income, cash_from_ops, depreciation, amortization, working_capital_changes,
            tolerance=0.01  # 1% tolerance
        )
        
        assert is_consistent is False
        assert error is not None
        assert difference > 0
    
    def test_validate_financial_ratios(self):
        """Test financial ratio validation."""
        revenue = 1000000
        ebitda = 500000
        net_income = 315000
        total_assets = 2000000
        
        industry_averages = {
            "ebitda_margin": 50.0,  # 50%
            "net_margin": 31.5,  # 31.5%
            "roa": 15.75  # 15.75%
        }
        
        results = validate_financial_ratios(
            revenue, ebitda, net_income, total_assets, industry_averages, threshold_bps=100.0
        )
        
        assert len(results) > 0
        # Should be within threshold since we're using exact industry averages
        for metric, is_within, msg in results:
            if metric != "industry_comparison":
                assert is_within is True
    
    def test_validate_financial_ratios_no_industry(self):
        """Test financial ratio validation without industry averages."""
        revenue = 1000000
        ebitda = 500000
        net_income = 315000
        total_assets = 2000000
        
        results = validate_financial_ratios(
            revenue, ebitda, net_income, total_assets, industry_averages=None
        )
        
        # Should return needs_industry_reference
        assert len(results) > 0
        has_reference_needed = any(
            metric == "industry_comparison" and not is_within 
            for metric, is_within, msg in results
        )
        assert has_reference_needed
    
    def test_check_historical_ranges(self):
        """Test historical range checking."""
        current_value = 1000000
        historical_values = [950000, 980000, 1020000, 1050000, 990000]
        
        is_within, message = check_historical_ranges(
            current_value, historical_values, "revenue", tolerance_percentage=0.20
        )
        
        assert is_within is True
        assert "revenue" in message.lower()
    
    def test_check_historical_ranges_outside(self):
        """Test historical range checking with value outside range."""
        current_value = 2000000  # Much higher than historical
        historical_values = [950000, 980000, 1020000, 1050000, 990000]
        
        is_within, message = check_historical_ranges(
            current_value, historical_values, "revenue", tolerance_percentage=0.20
        )
        
        assert is_within is False
        assert "outside" in message.lower() or "deviation" in message.lower()


if __name__ == "__main__":
    pytest.main([__file__])

