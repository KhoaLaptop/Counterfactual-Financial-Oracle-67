"""
Balance sheet constraint checker for financial validation.
"""

from typing import Dict, List, Optional, Tuple
import math


def check_balance_sheet_balance(
    assets: Dict[str, float],
    liabilities: Dict[str, float],
    equity: Dict[str, float],
    tolerance: float = 0.01
) -> Tuple[bool, Optional[str], float]:
    """
    Check if balance sheet balances: Assets = Liabilities + Equity
    
    Args:
        assets: Dictionary of asset accounts and values
        liabilities: Dictionary of liability accounts and values
        equity: Dictionary of equity accounts and values
        tolerance: Tolerance as percentage of total assets (default: 0.01 = 1%)
    
    Returns:
        Tuple of (is_balanced, error_message, imbalance_amount)
    """
    total_assets = sum(assets.values())
    total_liabilities = sum(liabilities.values())
    total_equity = sum(equity.values())
    
    total_liabilities_equity = total_liabilities + total_equity
    imbalance = abs(total_assets - total_liabilities_equity)
    
    if total_assets == 0:
        return (True, None, 0.0)
    
    imbalance_percentage = imbalance / total_assets
    
    if imbalance_percentage <= tolerance:
        return (True, None, imbalance)
    
    error_msg = (
        f"Balance sheet imbalance: Assets (${total_assets:,.2f}) != "
        f"Liabilities + Equity (${total_liabilities_equity:,.2f}). "
        f"Imbalance: ${imbalance:,.2f} ({imbalance_percentage * 100:.2f}% of assets)"
    )
    
    return (False, error_msg, imbalance)


def check_cash_flow_consistency(
    net_income: float,
    cash_from_ops: float,
    depreciation: float,
    amortization: float,
    working_capital_changes: float,
    other_adjustments: float = 0.0,
    tolerance: float = 0.05
) -> Tuple[bool, Optional[str], float]:
    """
    Check cash flow consistency: Cash from Ops should reconcile with Net Income + adjustments.
    
    Args:
        net_income: Net income
        cash_from_ops: Cash from operations (reported)
        depreciation: Depreciation expense
        amortization: Amortization expense
        working_capital_changes: Changes in working capital
        other_adjustments: Other adjustments (default: 0.0)
        tolerance: Tolerance as percentage of cash_from_ops (default: 0.05 = 5%)
    
    Returns:
        Tuple of (is_consistent, error_message, difference)
    """
    calculated_cfo = net_income + depreciation + amortization + working_capital_changes + other_adjustments
    difference = abs(cash_from_ops - calculated_cfo)
    
    if abs(cash_from_ops) == 0:
        if abs(calculated_cfo) < 1.0:
            return (True, None, difference)
        else:
            error_msg = (
                f"Cash flow inconsistency: Reported CFO is ${cash_from_ops:,.2f} but "
                f"calculated CFO is ${calculated_cfo:,.2f}. Difference: ${difference:,.2f}"
            )
            return (False, error_msg, difference)
    
    difference_percentage = difference / abs(cash_from_ops)
    
    if difference_percentage <= tolerance:
        return (True, None, difference)
    
    error_msg = (
        f"Cash flow inconsistency: Reported CFO (${cash_from_ops:,.2f}) != "
        f"Calculated CFO (${calculated_cfo:,.2f}). Difference: ${difference:,.2f} "
        f"({difference_percentage * 100:.2f}% of reported CFO)"
    )
    
    return (False, error_msg, difference)


def validate_financial_ratios(
    revenue: float,
    ebitda: float,
    net_income: float,
    total_assets: float,
    industry_averages: Optional[Dict[str, float]] = None,
    threshold_bps: float = 100.0
) -> List[Tuple[str, bool, str]]:
    """
    Validate financial ratios against industry averages.
    
    Args:
        revenue: Total revenue
        ebitda: EBITDA
        net_income: Net income
        total_assets: Total assets
        industry_averages: Dictionary of industry average ratios (default: None)
        threshold_bps: Threshold in basis points for flagging deviations (default: 100.0)
    
    Returns:
        List of (metric_name, is_within_threshold, message) tuples
    """
    results = []
    
    if revenue == 0:
        return results
    
    ebitda_margin = (ebitda / revenue) * 100 if revenue > 0 else 0.0
    net_margin = (net_income / revenue) * 100 if revenue > 0 else 0.0
    roa = (net_income / total_assets) * 100 if total_assets > 0 else 0.0
    
    if industry_averages:
        if "ebitda_margin" in industry_averages:
            industry_ebitda_margin = industry_averages["ebitda_margin"]
            deviation_bps = abs(ebitda_margin - industry_ebitda_margin) * 100
            is_within = deviation_bps <= threshold_bps
            msg = (
                f"EBITDA margin: {ebitda_margin:.2f}% vs industry {industry_ebitda_margin:.2f}% "
                f"(deviation: {deviation_bps:.0f} bps)"
            )
            results.append(("ebitda_margin", is_within, msg))
        
        if "net_margin" in industry_averages:
            industry_net_margin = industry_averages["net_margin"]
            deviation_bps = abs(net_margin - industry_net_margin) * 100
            is_within = deviation_bps <= threshold_bps
            msg = (
                f"Net margin: {net_margin:.2f}% vs industry {industry_net_margin:.2f}% "
                f"(deviation: {deviation_bps:.0f} bps)"
            )
            results.append(("net_margin", is_within, msg))
        
        if "roa" in industry_averages:
            industry_roa = industry_averages["roa"]
            deviation_bps = abs(roa - industry_roa) * 100
            is_within = deviation_bps <= threshold_bps
            msg = (
                f"ROA: {roa:.2f}% vs industry {industry_roa:.2f}% "
                f"(deviation: {deviation_bps:.0f} bps)"
            )
            results.append(("roa", is_within, msg))
    else:
        results.append(("industry_comparison", False, "needs_industry_reference"))
    
    return results


def check_historical_ranges(
    current_value: float,
    historical_values: List[float],
    metric_name: str,
    tolerance_percentage: float = 0.20
) -> Tuple[bool, str]:
    """
    Check if current value is within historical ranges.
    
    Args:
        current_value: Current value to check
        historical_values: List of historical values
        metric_name: Name of the metric being checked
        tolerance_percentage: Tolerance as percentage of historical range (default: 0.20 = 20%)
    
    Returns:
        Tuple of (is_within_range, message)
    """
    if not historical_values:
        return (True, f"No historical data available for {metric_name}")
    
    min_historical = min(historical_values)
    max_historical = max(historical_values)
    historical_range = max_historical - min_historical
    
    if historical_range == 0:
        if abs(current_value - min_historical) < 0.01:
            return (True, f"{metric_name} matches historical value")
        else:
            return (False, f"{metric_name} ({current_value}) differs from historical constant ({min_historical})")
    
    tolerance = historical_range * tolerance_percentage
    lower_bound = min_historical - tolerance
    upper_bound = max_historical + tolerance
    
    is_within = lower_bound <= current_value <= upper_bound
    
    if is_within:
        msg = (
            f"{metric_name} ({current_value}) is within historical range "
            f"([{min_historical:.2f}, {max_historical:.2f}]) with tolerance"
        )
    else:
        msg = (
            f"{metric_name} ({current_value}) is outside historical range "
            f"([{min_historical:.2f}, {max_historical:.2f}]) - deviation exceeds tolerance"
        )
    
    return (is_within, msg)

