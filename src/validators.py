"""
Output validation module for simulation results and pipeline outputs.
"""

import math
from typing import Dict, List, Tuple, Any, Optional


def validate_simulation_output(simulation_json: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate simulation output structure and values.
    
    Args:
        simulation_json: Simulation results dictionary
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check required fields
    required_fields = ["formula_projections", "monte_carlo", "assumption_log"]
    for field in required_fields:
        if field not in simulation_json:
            errors.append(f"Missing required field: {field}")
    
    # Validate formula projections
    fp = simulation_json.get("formula_projections", {})
    required_metrics = ["revenue", "ebitda", "net_income", "free_cash_flow", "npv"]
    
    for metric in required_metrics:
        if metric not in fp:
            errors.append(f"Missing formula projection: {metric}")
        else:
            entry = fp[metric]
            if not isinstance(entry, dict):
                errors.append(f"Invalid structure for {metric}: expected dict, got {type(entry)}")
                continue
            
            value = entry.get("value")
            if value is None:
                errors.append(f"Missing value for {metric}")
            elif not isinstance(value, (int, float)):
                errors.append(f"Invalid value type for {metric}: {type(value)}, expected numeric")
            else:
                # Check for NaN/Inf
                if math.isnan(value):
                    errors.append(f"NaN value for {metric}")
                elif math.isinf(value):
                    errors.append(f"Infinite value for {metric}")
            
            # Check formula field exists
            if "formula" not in entry:
                errors.append(f"Missing formula for {metric}")
    
    # Validate Monte Carlo results
    mc = simulation_json.get("monte_carlo", {})
    if not isinstance(mc, dict):
        errors.append("Monte Carlo section is not a dictionary")
    else:
        results = mc.get("results", {})
        if not isinstance(results, dict):
            errors.append("Monte Carlo results is not a dictionary")
        else:
            mc_metrics = ["revenue", "ebitda", "free_cash_flow", "npv"]
            for metric in mc_metrics:
                if metric not in results:
                    errors.append(f"Missing Monte Carlo result for {metric}")
                else:
                    metric_data = results[metric]
                    if not isinstance(metric_data, dict):
                        errors.append(f"Invalid structure for Monte Carlo {metric}")
                        continue
                    
                    # Check required percentiles
                    for percentile in ["median", "p10", "p90"]:
                        if percentile not in metric_data:
                            errors.append(f"Missing {percentile} for Monte Carlo {metric}")
                        else:
                            value = metric_data[percentile]
                            if not isinstance(value, (int, float)):
                                errors.append(f"Invalid {percentile} type for {metric}: {type(value)}")
                            elif math.isnan(value):
                                errors.append(f"NaN {percentile} for {metric}")
                            elif math.isinf(value):
                                errors.append(f"Infinite {percentile} for {metric}")
                    
                    # Validate percentile ordering: p10 <= median <= p90
                    if all(k in metric_data for k in ["p10", "median", "p90"]):
                        p10 = metric_data["p10"]
                        median = metric_data["median"]
                        p90 = metric_data["p90"]
                        
                        if not (p10 <= median <= p90):
                            errors.append(
                                f"Invalid percentile ordering for {metric}: "
                                f"p10={p10}, median={median}, p90={p90}"
                            )
    
    # Validate assumption log
    assumption_log = simulation_json.get("assumption_log", [])
    if not isinstance(assumption_log, list):
        errors.append("Assumption log is not a list")
    
    return (len(errors) == 0, errors)


def validate_monte_carlo_results(results: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate Monte Carlo output reasonableness.
    
    Args:
        results: Monte Carlo results dictionary
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    if not isinstance(results, dict):
        errors.append("Monte Carlo results must be a dictionary")
        return (False, errors)
    
    for metric, data in results.items():
        if not isinstance(data, dict):
            errors.append(f"Invalid structure for {metric}")
            continue
        
        # Check required fields
        required = ["median", "p10", "p90"]
        for field in required:
            if field not in data:
                errors.append(f"Missing {field} for {metric}")
                continue
            
            value = data[field]
            if not isinstance(value, (int, float)):
                errors.append(f"Invalid {field} type for {metric}: {type(value)}")
            elif math.isnan(value):
                errors.append(f"NaN {field} for {metric}")
            elif math.isinf(value):
                errors.append(f"Infinite {field} for {metric}")
        
        # Check percentile ordering
        if all(k in data for k in required):
            p10 = data["p10"]
            median = data["median"]
            p90 = data["p90"]
            
            if not (p10 <= median <= p90):
                errors.append(
                    f"Invalid percentile ordering for {metric}: "
                    f"p10={p10}, median={median}, p90={p90}"
                )
            
            # Check for reasonable ranges (warn if spread is too large or too small)
            spread = p90 - p10
            if spread < 0:
                errors.append(f"Negative spread for {metric}: p90={p90}, p10={p10}")
            elif median != 0 and abs(spread / median) > 10:
                # Spread is more than 10x the median - might be reasonable but worth checking
                pass  # This is a warning, not an error
    
    return (len(errors) == 0, errors)


def validate_critic_output(critic_json: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate critic output structure and values.
    
    Args:
        critic_json: Critic results dictionary
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check verdict
    verdict = critic_json.get("verdict")
    if verdict not in ["approve", "revise"]:
        errors.append(f"Invalid verdict: {verdict}, must be 'approve' or 'revise'")
    
    # Check constraint_checks
    constraint_checks = critic_json.get("constraint_checks", {})
    if not isinstance(constraint_checks, dict):
        errors.append("constraint_checks must be a dictionary")
    else:
        # Check balance sheet
        bs_check = constraint_checks.get("balance_sheet", {})
        if not isinstance(bs_check, dict):
            errors.append("balance_sheet check must be a dictionary")
        else:
            if "is_balanced" not in bs_check:
                errors.append("Missing is_balanced in balance_sheet check")
            elif not isinstance(bs_check["is_balanced"], bool):
                errors.append("is_balanced must be a boolean")
        
        # Check cash flow
        cf_check = constraint_checks.get("cash_flow", {})
        if not isinstance(cf_check, dict):
            errors.append("cash_flow check must be a dictionary")
        else:
            if "is_consistent" not in cf_check:
                errors.append("Missing is_consistent in cash_flow check")
            elif not isinstance(cf_check["is_consistent"], bool):
                errors.append("is_consistent must be a boolean")
    
    # Check suggested_fixes if verdict is revise
    if verdict == "revise":
        suggested_fixes = critic_json.get("suggested_fixes", [])
        if not isinstance(suggested_fixes, list):
            errors.append("suggested_fixes must be a list")
        elif len(suggested_fixes) == 0:
            errors.append("suggested_fixes is empty but verdict is 'revise'")
        else:
            for i, fix in enumerate(suggested_fixes):
                if not isinstance(fix, dict):
                    errors.append(f"suggested_fixes[{i}] must be a dictionary")
                else:
                    if "issue" not in fix:
                        errors.append(f"suggested_fixes[{i}] missing 'issue' field")
                    if "fix" not in fix:
                        errors.append(f"suggested_fixes[{i}] missing 'fix' field")
    
    return (len(errors) == 0, errors)


def validate_evaluation_output(evaluation_json: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate evaluation output structure and values.
    
    Args:
        evaluation_json: Evaluation results dictionary
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check status
    status = evaluation_json.get("status")
    if status not in ["approved", "revised"]:
        errors.append(f"Invalid status: {status}, must be 'approved' or 'revised'")
    
    # Check final_simulation
    final_simulation = evaluation_json.get("final_simulation")
    if final_simulation is None:
        errors.append("Missing final_simulation")
    elif isinstance(final_simulation, dict):
        # Validate the final simulation output (but don't fail if it's minimal - just warn)
        is_valid, sim_errors = validate_simulation_output(final_simulation)
        if not is_valid:
            # Only add critical errors, not missing optional fields
            critical_errors = [e for e in sim_errors if "NaN" in e or "Infinite" in e or "percentile ordering" in e.lower()]
            if critical_errors:
                errors.extend([f"final_simulation: {e}" for e in critical_errors])
    
    # Check applied_fixes
    applied_fixes = evaluation_json.get("applied_fixes", [])
    if not isinstance(applied_fixes, list):
        errors.append("applied_fixes must be a list")
    
    return (len(errors) == 0, errors)


def validate_user_controls(user_controls: Dict[str, float]) -> Tuple[bool, List[str]]:
    """
    Validate user control inputs for reasonableness.
    
    Args:
        user_controls: User control dictionary
        
    Returns:
        Tuple of (is_valid, list_of_warnings)
    """
    warnings = []
    
    # Check opex_delta_bps
    opex_delta = user_controls.get("opex_delta_bps", 0.0)
    if not isinstance(opex_delta, (int, float)):
        warnings.append(f"Invalid opex_delta_bps type: {type(opex_delta)}")
    elif abs(opex_delta) > 1000:
        warnings.append(f"Extreme opex_delta_bps: {opex_delta} bps (>1000 bps)")
    
    # Check revenue_delta_bps
    revenue_delta = user_controls.get("revenue_delta_bps", 0.0)
    if not isinstance(revenue_delta, (int, float)):
        warnings.append(f"Invalid revenue_delta_bps type: {type(revenue_delta)}")
    elif abs(revenue_delta) > 1000:
        warnings.append(f"Extreme revenue_delta_bps: {revenue_delta} bps (>1000 bps)")
    
    # Check discount_rate_base
    discount_rate_base = user_controls.get("discount_rate_base", 0.08)
    if not isinstance(discount_rate_base, (int, float)):
        warnings.append(f"Invalid discount_rate_base type: {type(discount_rate_base)}")
    elif discount_rate_base < 0:
        warnings.append(f"Negative discount_rate_base: {discount_rate_base}")
    elif discount_rate_base > 1.0:
        warnings.append(f"Discount rate > 100%: {discount_rate_base}")
    
    # Check discount_rate_delta_bps
    discount_rate_delta = user_controls.get("discount_rate_delta_bps", 0.0)
    if not isinstance(discount_rate_delta, (int, float)):
        warnings.append(f"Invalid discount_rate_delta_bps type: {type(discount_rate_delta)}")
    elif abs(discount_rate_delta) > 1000:
        warnings.append(f"Extreme discount_rate_delta_bps: {discount_rate_delta} bps (>1000 bps)")
    
    # Check final discount rate
    final_discount_rate = discount_rate_base + (discount_rate_delta / 10000)
    if final_discount_rate < 0:
        warnings.append(f"Final discount rate is negative: {final_discount_rate}")
    elif final_discount_rate > 1.0:
        warnings.append(f"Final discount rate > 100%: {final_discount_rate}")
    
    return (len(warnings) == 0, warnings)

