"""
Financial formula utilities for calculations and projections.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
import math


def calculate_ebitda(revenue: float, opex: float, cogs: float = 0.0) -> float:
    """
    Calculate EBITDA = Revenue - COGS - OpEx
    
    Args:
        revenue: Total revenue
        opex: Operating expenses
        cogs: Cost of goods sold (default: 0)
    
    Returns:
        EBITDA value
    """
    return revenue - cogs - opex


def calculate_ebit(ebitda: float, depreciation: float, amortization: float = 0.0) -> float:
    """
    Calculate EBIT = EBITDA - Depreciation - Amortization
    
    Args:
        ebitda: Earnings before interest, taxes, depreciation, and amortization
        depreciation: Depreciation expense
        amortization: Amortization expense (default: 0)
    
    Returns:
        EBIT value
    """
    return ebitda - depreciation - amortization


def calculate_net_income(
    ebit: float,
    interest_expense: float,
    tax_rate: float,
    other_income: float = 0.0
) -> float:
    """
    Calculate Net Income = (EBIT - Interest Expense + Other Income) * (1 - Tax Rate)
    
    Args:
        ebit: Earnings before interest and taxes
        interest_expense: Interest expense
        tax_rate: Tax rate as decimal (e.g., 0.25 for 25%)
        other_income: Other income/expense (default: 0)
    
    Returns:
        Net income value
    """
    ebt = ebit - interest_expense + other_income
    return ebt * (1 - tax_rate)


def calculate_free_cash_flow(
    net_income: float,
    depreciation: float,
    amortization: float,
    capex: float,
    working_capital_delta: float = 0.0,
    other_adjustments: float = 0.0
) -> float:
    """
    Calculate Free Cash Flow = Net Income + D&A - CapEx - ΔWorking Capital + Other Adjustments
    
    Args:
        net_income: Net income
        depreciation: Depreciation expense
        amortization: Amortization expense
        capex: Capital expenditures
        working_capital_delta: Change in working capital (default: 0)
        other_adjustments: Other cash flow adjustments (default: 0)
    
    Returns:
        Free cash flow value
    """
    return net_income + depreciation + amortization - capex - working_capital_delta + other_adjustments


def calculate_npv(
    cash_flows: List[float],
    discount_rate: float,
    initial_investment: float = 0.0
) -> float:
    """
    Calculate Net Present Value of cash flows.
    
    Args:
        cash_flows: List of future cash flows
        discount_rate: Discount rate as decimal (e.g., 0.08 for 8%)
        initial_investment: Initial investment (default: 0)
    
    Returns:
        NPV value
    """
    npv = -initial_investment
    for i, cf in enumerate(cash_flows, start=1):
        npv += cf / ((1 + discount_rate) ** i)
    return npv


def calculate_irr(cash_flows: List[float], initial_guess: float = 0.1) -> Optional[float]:
    """
    Calculate Internal Rate of Return using Newton-Raphson method.
    
    Args:
        cash_flows: List of cash flows (first is typically negative initial investment)
        initial_guess: Initial guess for IRR (default: 0.1)
    
    Returns:
        IRR value or None if calculation fails
    """
    try:
        return np.irr(cash_flows) if hasattr(np, 'irr') else _calculate_irr_manual(cash_flows, initial_guess)
    except:
        return _calculate_irr_manual(cash_flows, initial_guess)


def _calculate_irr_manual(cash_flows: List[float], initial_guess: float = 0.1) -> Optional[float]:
    """Manual IRR calculation using Newton-Raphson."""
    def npv_func(rate):
        return sum(cf / ((1 + rate) ** i) for i, cf in enumerate(cash_flows))
    
    def npv_derivative(rate):
        return sum(-i * cf / ((1 + rate) ** (i + 1)) for i, cf in enumerate(cash_flows))
    
    rate = initial_guess
    for _ in range(100):
        npv_val = npv_func(rate)
        if abs(npv_val) < 1e-6:
            return rate
        derivative = npv_derivative(rate)
        if abs(derivative) < 1e-10:
            break
        rate = rate - npv_val / derivative
        if rate < -0.99 or rate > 10:
            break
    
    return None


def apply_delta_percentage(value: float, delta_bps: float) -> float:
    """
    Apply a delta in basis points (bps) to a value.
    
    Args:
        value: Original value
        delta_bps: Delta in basis points (e.g., -50 for -50 bps = -0.5%)
    
    Returns:
        Adjusted value
    """
    return value * (1 + delta_bps / 10000)


def calculate_percentiles(values: List[float], percentiles: List[int] = [10, 50, 90]) -> Dict[int, float]:
    """
    Calculate percentiles for a list of values.
    
    Args:
        values: List of numeric values
        percentiles: List of percentile values to calculate (default: [10, 50, 90])
    
    Returns:
        Dictionary mapping percentile to value
    """
    if not values:
        return {p: 0.0 for p in percentiles}
    
    sorted_values = sorted(values)
    result = {}
    for p in percentiles:
        idx = (p / 100) * (len(sorted_values) - 1)
        if idx.is_integer():
            result[p] = sorted_values[int(idx)]
        else:
            lower = sorted_values[int(idx)]
            upper = sorted_values[int(idx) + 1] if int(idx) + 1 < len(sorted_values) else lower
            result[p] = lower + (upper - lower) * (idx - int(idx))
    
    return result


def monte_carlo_simulation(
    base_value: float,
    num_scenarios: int = 10000,
    mean_delta: float = 0.0,
    std_delta: float = 0.01,
    distribution: str = "normal"
) -> List[float]:
    """
    Generate Monte Carlo scenarios for a base value.
    
    Args:
        base_value: Base value to simulate around
        num_scenarios: Number of scenarios to generate (default: 10000)
        mean_delta: Mean of the delta distribution (default: 0.0)
        std_delta: Standard deviation of the delta distribution (default: 0.01)
        distribution: Distribution type ("normal" or "uniform") (default: "normal")
    
    Returns:
        List of simulated values
    """
    if distribution == "normal":
        deltas = np.random.normal(mean_delta, std_delta, num_scenarios)
    elif distribution == "uniform":
        deltas = np.random.uniform(mean_delta - std_delta, mean_delta + std_delta, num_scenarios)
    else:
        raise ValueError(f"Unsupported distribution: {distribution}")
    
    return [base_value * (1 + d) for d in deltas]

