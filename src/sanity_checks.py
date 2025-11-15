"""
Sanity checks for financial data before LLM processing.
"""

from typing import Dict, List, Tuple, Any, Optional


def check_financial_sanity(report_json: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Perform sanity checks on financial data before LLM processing.
    
    Args:
        report_json: Report JSON dictionary
        
    Returns:
        Tuple of (is_sane, list_of_warnings)
    """
    warnings = []
    
    # Extract key values
    income_statement = report_json.get("income_statement", {})
    revenue = income_statement.get("revenue") or income_statement.get("total_revenue", 0)
    opex = income_statement.get("opex") or income_statement.get("operating_expenses", 0)
    cogs = income_statement.get("cogs") or income_statement.get("cost_of_goods_sold", 0)
    ebitda = income_statement.get("ebitda", 0)
    net_income = income_statement.get("net_income", 0)
    
    # Check 1: OpEx > Revenue
    if revenue > 0 and opex > revenue:
        warnings.append(
            f"⚠️ SANITY CHECK FAILED: OpEx (${opex:,.2f}) > Revenue (${revenue:,.2f}). "
            f"This indicates a loss-making scenario or data error."
        )
    
    # Check 2: COGS > Revenue
    if revenue > 0 and cogs > revenue:
        warnings.append(
            f"⚠️ SANITY CHECK FAILED: COGS (${cogs:,.2f}) > Revenue (${revenue:,.2f}). "
            f"This indicates negative gross margin or data error."
        )
    
    # Check 3: EBITDA Margin > 100%
    if revenue > 0:
        ebitda_margin = (ebitda / revenue) * 100 if ebitda else 0
        if ebitda_margin > 100:
            warnings.append(
                f"⚠️ SANITY CHECK FAILED: EBITDA Margin ({ebitda_margin:.2f}%) > 100%. "
                f"This is physically impossible. EBITDA cannot exceed revenue."
            )
        elif ebitda_margin < -50:
            warnings.append(
                f"⚠️ SANITY CHECK WARNING: EBITDA Margin ({ebitda_margin:.2f}%) < -50%. "
                f"Extremely negative margin may indicate data error."
            )
    
    # Check 4: Net Income Margin > 100%
    if revenue > 0:
        net_margin = (net_income / revenue) * 100 if net_income else 0
        if net_margin > 100:
            warnings.append(
                f"⚠️ SANITY CHECK FAILED: Net Income Margin ({net_margin:.2f}%) > 100%. "
                f"This is physically impossible."
            )
        elif net_margin < -100:
            warnings.append(
                f"⚠️ SANITY CHECK WARNING: Net Income Margin ({net_margin:.2f}%) < -100%. "
                f"Extremely negative margin may indicate data error."
            )
    
    # Check 5: Negative Revenue
    if revenue < 0:
        warnings.append(
            f"⚠️ SANITY CHECK WARNING: Revenue is negative (${revenue:,.2f}). "
            f"This may be valid for certain scenarios but is unusual."
        )
    
    # Check 6: Total Expenses > 2x Revenue
    total_expenses = opex + cogs
    if revenue > 0 and total_expenses > 2 * revenue:
        warnings.append(
            f"⚠️ SANITY CHECK WARNING: Total Expenses (${total_expenses:,.2f}) > 2x Revenue (${revenue:,.2f}). "
            f"This indicates severe losses or potential data error."
        )
    
    # Check 7: Balance Sheet Sanity
    balance_sheet = report_json.get("balance_sheet", {})
    if balance_sheet:
        assets = balance_sheet.get("assets", {})
        liabilities = balance_sheet.get("liabilities", {})
        equity = balance_sheet.get("equity", {})
        
        total_assets = sum(assets.values()) if isinstance(assets, dict) else 0
        total_liabilities = sum(liabilities.values()) if isinstance(liabilities, dict) else 0
        total_equity = sum(equity.values()) if isinstance(equity, dict) else 0
        
        # Check for negative equity (may be valid but unusual)
        if total_equity < 0:
            warnings.append(
                f"⚠️ SANITY CHECK WARNING: Total Equity is negative (${total_equity:,.2f}). "
                f"This may indicate insolvency or data error."
            )
        
        # Check for negative assets
        if total_assets < 0:
            warnings.append(
                f"⚠️ SANITY CHECK FAILED: Total Assets is negative (${total_assets:,.2f}). "
                f"This is physically impossible."
            )
    
    # Check 8: Cash Flow Sanity
    cash_flow = report_json.get("cash_flow", {})
    if cash_flow:
        cash_from_ops = cash_flow.get("cash_from_operations") or cash_flow.get("operating_cash_flow", 0)
        if revenue > 0:
            cfo_margin = (cash_from_ops / revenue) * 100 if cash_from_ops else 0
            if abs(cfo_margin) > 200:
                warnings.append(
                    f"⚠️ SANITY CHECK WARNING: Cash from Operations Margin ({cfo_margin:.2f}%) is extreme. "
                    f"May indicate data error or unusual business model."
                )
    
    return (len(warnings) == 0, warnings)


def check_simulation_sanity(
    simulation_json: Dict[str, Any],
    report_json: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """
    Perform sanity checks on simulation outputs.
    
    Args:
        simulation_json: Simulation results
        report_json: Original report JSON
        
    Returns:
        Tuple of (is_sane, list_of_warnings)
    """
    warnings = []
    
    # Get base revenue for comparison
    income_statement = report_json.get("income_statement", {})
    base_revenue = income_statement.get("revenue") or income_statement.get("total_revenue", 0)
    
    # Check formula projections
    formula_projections = simulation_json.get("formula_projections", {})
    
    # Check revenue projection
    if "revenue" in formula_projections:
        projected_revenue = formula_projections["revenue"].get("value", 0)
        if base_revenue > 0:
            revenue_change = ((projected_revenue - base_revenue) / base_revenue) * 100
            if abs(revenue_change) > 1000:  # > 1000% change
                warnings.append(
                    f"⚠️ SANITY CHECK WARNING: Projected revenue change is extreme ({revenue_change:.2f}%). "
                    f"Base: ${base_revenue:,.2f}, Projected: ${projected_revenue:,.2f}"
                )
    
    # Check EBITDA margin
    if "revenue" in formula_projections and "ebitda" in formula_projections:
        revenue_val = formula_projections["revenue"].get("value", 0)
        ebitda_val = formula_projections["ebitda"].get("value", 0)
        if revenue_val > 0:
            ebitda_margin = (ebitda_val / revenue_val) * 100
            if ebitda_margin > 100:
                warnings.append(
                    f"⚠️ SANITY CHECK FAILED: Projected EBITDA Margin ({ebitda_margin:.2f}%) > 100%. "
                    f"This is physically impossible."
                )
    
    # Check NPV reasonableness
    if "npv" in formula_projections:
        npv_val = formula_projections["npv"].get("value", 0)
        if base_revenue > 0:
            # NPV should generally be within reasonable multiple of revenue
            npv_to_revenue_ratio = abs(npv_val / base_revenue) if base_revenue > 0 else 0
            if npv_to_revenue_ratio > 50:  # NPV > 50x revenue
                warnings.append(
                    f"⚠️ SANITY CHECK WARNING: NPV to Revenue ratio is very high ({npv_to_revenue_ratio:.2f}x). "
                    f"This may indicate unrealistic projections."
                )
    
    # Check Monte Carlo results
    monte_carlo = simulation_json.get("monte_carlo", {}).get("results", {})
    for metric, data in monte_carlo.items():
        if isinstance(data, dict):
            median = data.get("median", 0)
            p10 = data.get("p10", 0)
            p90 = data.get("p90", 0)
            
            # Check for extreme spreads
            if median != 0:
                spread_ratio = (p90 - p10) / abs(median) if median != 0 else 0
                if spread_ratio > 5:  # Spread > 5x median
                    warnings.append(
                        f"⚠️ SANITY CHECK WARNING: Monte Carlo spread for {metric} is very wide "
                        f"({spread_ratio:.2f}x median). This indicates high uncertainty."
                    )
    
    return (len(warnings) == 0, warnings)


def check_user_controls_sanity(user_controls: Dict[str, float]) -> Tuple[bool, List[str]]:
    """
    Perform sanity checks on user controls.
    
    Args:
        user_controls: User control dictionary
        
    Returns:
        Tuple of (is_sane, list_of_warnings)
    """
    warnings = []
    
    opex_delta = user_controls.get("opex_delta_bps", 0)
    revenue_delta = user_controls.get("revenue_delta_bps", 0)
    discount_rate_base = user_controls.get("discount_rate_base", 0.08)
    discount_rate_delta = user_controls.get("discount_rate_delta_bps", 0)
    
    # Check extreme deltas
    if abs(opex_delta) > 5000:  # > 50% change
        warnings.append(
            f"⚠️ SANITY CHECK WARNING: OpEx delta ({opex_delta} bps = {opex_delta/100:.1f}%) is extreme. "
            f"This may produce unrealistic results."
        )
    
    if abs(revenue_delta) > 5000:  # > 50% change
        warnings.append(
            f"⚠️ SANITY CHECK WARNING: Revenue delta ({revenue_delta} bps = {revenue_delta/100:.1f}%) is extreme. "
            f"This may produce unrealistic results."
        )
    
    # Check discount rate
    final_discount_rate = discount_rate_base + (discount_rate_delta / 10000)
    if final_discount_rate < 0:
        warnings.append(
            f"⚠️ SANITY CHECK FAILED: Final discount rate ({final_discount_rate*100:.2f}%) is negative. "
            f"This is invalid for DCF calculations."
        )
    elif final_discount_rate > 1.0:
        warnings.append(
            f"⚠️ SANITY CHECK FAILED: Final discount rate ({final_discount_rate*100:.2f}%) > 100%. "
            f"This is invalid."
        )
    elif final_discount_rate > 0.5:  # > 50%
        warnings.append(
            f"⚠️ SANITY CHECK WARNING: Final discount rate ({final_discount_rate*100:.2f}%) is very high. "
            f"This may produce unrealistic valuations."
        )
    
    return (len(warnings) == 0, warnings)

