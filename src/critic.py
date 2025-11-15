"""
DeepSeek critic module for financial analysis validation.
"""

import os
import json
import asyncio
from typing import Dict, List, Optional, Any
import aiohttp
from dotenv import load_dotenv

from .balance_sheet_checker import (
    check_balance_sheet_balance,
    check_cash_flow_consistency,
    validate_financial_ratios,
    check_historical_ranges
)
from .validators import validate_critic_output

load_dotenv()


CRITIC_PROMPT = """You are a senior financial report analyst who performs rigorous, forensic reviews.

You will receive:

- `report_json` (original extraction),
- `simulation_json` (OpenAI simulation results, formula_projections, monte_carlo, assumption_log, traceability).

Your tasks:

1) Constraint checks (must run automatically):
   - Verify balance sheet balancing for baseline and each scenario sample median. If imbalance > $X or > 1% of assets, report exact mismatches and root cause.
   - Check cash flow consistency (Net Income → Cash from ops adjustments → Free cash flow).

2) Comparative analysis:
   - Compare reported KPI(s) vs industry averages (if industry avg present in report_json or from user input). Flag deviations > 100 bps with required justification.
   - If industry averages are not present, return `needs_industry_reference`.

3) Explainability / evidence:
   - For each major projection and assumption, require the simulation to provide supporting doc sections. Mark any unsupported assumption as `unsupported`.

4) Sanity tests:
   - Check whether simulated growth rates, margins, or discount rates are within historical ranges (3-year) found in the report or from input.

5) Verdict & corrective directions:
   - Verdict `approve` or `revise`.
   - If `revise`, provide explicit correction instructions (e.g., "reduce long-term revenue growth to X% and recalc NPV using Y formula; check CapEx entries in balance_sheet.notes[CapExTable]").

Return your response as a valid JSON object with the following structure:
{
  "verdict": "approve" or "revise",
  "constraint_checks": {
    "balance_sheet": {"is_balanced": true/false, "error": "...", "imbalance": 0.0},
    "cash_flow": {"is_consistent": true/false, "error": "...", "difference": 0.0}
  },
  "comparative_analysis": {
    "industry_comparison": {...},
    "deviations": [...]
  },
  "explainability": {
    "supported_assumptions": [...],
    "unsupported_assumptions": [...]
  },
  "sanity_tests": {
    "growth_rates": {"is_valid": true/false, "message": "..."},
    "margins": {"is_valid": true/false, "message": "..."},
    "discount_rates": {"is_valid": true/false, "message": "..."}
  },
  "suggested_fixes": [
    {"issue": "...", "fix": "...", "formula": "..."},
    ...
  ]
}
"""


class CriticEngine:
    """DeepSeek critic engine for financial analysis validation."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize critic engine.
        
        Args:
            api_key: DeepSeek API key (default: from environment)
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DeepSeek API key not provided")
        
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
    
    async def run_critique(
        self,
        report_json: Dict[str, Any],
        simulation_json: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run critique on simulation results.
        
        Args:
            report_json: Original report JSON
            simulation_json: Simulation results from OpenAI
        
        Returns:
            Critique results dictionary
        """
        # Run local constraint checks first
        local_checks = self._run_local_constraint_checks(report_json, simulation_json)
        
        # Prepare input for DeepSeek
        input_data = {
            "report_json": report_json,
            "simulation_json": simulation_json,
            "local_checks": local_checks
        }
        
        # Call DeepSeek API
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": "deepseek-chat",
                    "messages": [
                        {
                            "role": "system",
                            "content": CRITIC_PROMPT
                        },
                        {
                            "role": "user",
                            "content": json.dumps(input_data)
                        }
                    ],
                    "temperature": 0.3
                }
                
                async with session.post(self.api_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result["choices"][0]["message"]["content"]
                        critic_json = json.loads(content)
                        
                        # Merge with local checks
                        critic_json["local_checks"] = local_checks
                        
                        # Validate critic output
                        is_valid, errors = validate_critic_output(critic_json)
                        if not is_valid:
                            print(f"[WARNING] Critic output validation found {len(errors)} issue(s):")
                            for error in errors[:5]:
                                print(f"  - {error}")
                        
                        return critic_json
                    else:
                        error_text = await response.text()
                        print(f"DeepSeek API error: {response.status}, {error_text}")
                        return self._create_fallback_critique(local_checks)
        
        except Exception as e:
            print(f"DeepSeek API error: {e}, using local checks only")
            critic_json = self._create_fallback_critique(local_checks)
            
            # Validate fallback critic output
            is_valid, errors = validate_critic_output(critic_json)
            if not is_valid:
                print(f"[WARNING] Fallback critic output validation found {len(errors)} issue(s):")
                for error in errors[:5]:
                    print(f"  - {error}")
            
            return critic_json
    
    def _run_local_constraint_checks(
        self,
        report_json: Dict[str, Any],
        simulation_json: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run local constraint checks."""
        checks = {
            "balance_sheet": {"is_balanced": True, "error": None, "imbalance": 0.0},
            "cash_flow": {"is_consistent": True, "error": None, "difference": 0.0},
            "financial_ratios": [],
            "historical_ranges": []
        }
        
        # Check balance sheet
        if "balance_sheet" in report_json:
            bs = report_json["balance_sheet"]
            assets = bs.get("assets", {})
            liabilities = bs.get("liabilities", {})
            equity = bs.get("equity", {})
            
            if isinstance(assets, dict) and isinstance(liabilities, dict) and isinstance(equity, dict):
                is_balanced, error, imbalance = check_balance_sheet_balance(
                    assets, liabilities, equity
                )
                checks["balance_sheet"] = {
                    "is_balanced": is_balanced,
                    "error": error,
                    "imbalance": imbalance
                }
        
        # Check cash flow consistency
        if "cash_flow" in report_json and "income_statement" in report_json:
            cf = report_json["cash_flow"]
            is_data = report_json["income_statement"]
            
            net_income = is_data.get("net_income", 0.0)
            cash_from_ops = cf.get("cash_from_operations", cf.get("operating_cash_flow", 0.0))
            depreciation = cf.get("depreciation", is_data.get("depreciation", 0.0))
            amortization = cf.get("amortization", is_data.get("amortization", 0.0))
            working_capital_changes = cf.get("working_capital_changes", 0.0)
            
            is_consistent, error, difference = check_cash_flow_consistency(
                net_income, cash_from_ops, depreciation, amortization, working_capital_changes
            )
            checks["cash_flow"] = {
                "is_consistent": is_consistent,
                "error": error,
                "difference": difference
            }
        
        # Check financial ratios
        if "income_statement" in report_json and "balance_sheet" in report_json:
            is_data = report_json["income_statement"]
            bs = report_json["balance_sheet"]
            
            revenue = is_data.get("revenue", is_data.get("total_revenue", 0.0))
            ebitda = is_data.get("ebitda", 0.0)
            net_income = is_data.get("net_income", 0.0)
            total_assets = bs.get("total_assets", 0.0)
            
            industry_averages = report_json.get("industry_averages", {})
            ratio_results = validate_financial_ratios(
                revenue, ebitda, net_income, total_assets, industry_averages
            )
            checks["financial_ratios"] = ratio_results
        
        return checks
    
    def _create_fallback_critique(self, local_checks: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback critique based on local checks only."""
        verdict = "approve"
        suggested_fixes = []
        
        # Determine verdict based on local checks
        if not local_checks["balance_sheet"]["is_balanced"]:
            verdict = "revise"
            suggested_fixes.append({
                "issue": "Balance sheet imbalance",
                "fix": local_checks["balance_sheet"]["error"],
                "formula": "Assets = Liabilities + Equity"
            })
        
        if not local_checks["cash_flow"]["is_consistent"]:
            verdict = "revise"
            suggested_fixes.append({
                "issue": "Cash flow inconsistency",
                "fix": local_checks["cash_flow"]["error"],
                "formula": "Cash from Ops = Net Income + D&A + Working Capital Changes"
            })
        
        return {
            "verdict": verdict,
            "constraint_checks": local_checks,
            "comparative_analysis": {
                "industry_comparison": {},
                "deviations": []
            },
            "explainability": {
                "supported_assumptions": [],
                "unsupported_assumptions": []
            },
            "sanity_tests": {
                "growth_rates": {"is_valid": True, "message": "Not checked"},
                "margins": {"is_valid": True, "message": "Not checked"},
                "discount_rates": {"is_valid": True, "message": "Not checked"}
            },
            "suggested_fixes": suggested_fixes,
            "local_checks": local_checks
        }

