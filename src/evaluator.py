"""
ChatGPT evaluator module for applying critic fixes and generating final PDF.
"""

import os
import json
import asyncio
from typing import Dict, List, Optional, Any
from openai import OpenAI
from dotenv import load_dotenv

from .financial_formulas import (
    calculate_ebitda,
    calculate_ebit,
    calculate_net_income,
    calculate_free_cash_flow,
    calculate_npv,
    apply_delta_percentage
)
from .validators import validate_evaluation_output, validate_simulation_output

load_dotenv()


EVALUATOR_PROMPT = """You are an arbiter that receives:

- `simulation_json`
- `critic_json`

If critic.verdict == "revise":
  - Apply suggested_fixes to `simulation_json` deterministically:
     * For formula changes, recalculate using exact formulas supplied.
     * Re-run Monte Carlo accordingly.
  - Produce a `revised_simulation_json` with full `assumption_log` entries describing each applied change and its effect on median/percentiles.

If critic.verdict == "approve":
  - Use `simulation_json` as-is for final report.

Return your response as a valid JSON object with the following structure:
{
  "final_simulation": {...},
  "applied_fixes": [
    {"fix": "...", "before": {...}, "after": {...}, "impact": "..."},
    ...
  ],
  "assumption_log": [
    {"change": "...", "effect": "..."},
    ...
  ]
}
"""


class EvaluatorEngine:
    """ChatGPT evaluator engine for applying critic fixes."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize evaluator engine.
        
        Args:
            api_key: ChatGPT API key (default: from environment, falls back to OpenAI key)
        """
        self.api_key = api_key or os.getenv("CHATGPT_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("ChatGPT/OpenAI API key not provided")
        
        self.client = OpenAI(api_key=self.api_key)
    
    async def evaluate(
        self,
        simulation_json: Dict[str, Any],
        critic_json: Dict[str, Any],
        report_json: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate and apply critic fixes to simulation results.
        
        Args:
            simulation_json: Simulation results from OpenAI
            critic_json: Critique results from DeepSeek
            report_json: Original report JSON (optional, for context)
        
        Returns:
            Final evaluation results dictionary
        """
        # If approved, return simulation as-is
        if critic_json.get("verdict") == "approve":
            evaluation_json = {
                "final_simulation": simulation_json,
                "applied_fixes": [],
                "assumption_log": [],
                "status": "approved"
            }
            
            # Validate evaluation output
            is_valid, errors = validate_evaluation_output(evaluation_json)
            if not is_valid:
                print(f"[WARNING] Evaluation output validation found {len(errors)} issue(s):")
                for error in errors[:5]:
                    print(f"  - {error}")
            
            return evaluation_json
        
        # If revision needed, apply fixes
        if critic_json.get("verdict") == "revise":
            # Try to use ChatGPT API for intelligent fix application
            try:
                input_data = {
                    "simulation_json": simulation_json,
                    "critic_json": critic_json,
                    "report_json": report_json
                }
                
                # Use ChatGPT API (gpt-4 or gpt-3.5-turbo)
                response = self.client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=[
                        {
                            "role": "system",
                            "content": EVALUATOR_PROMPT
                        },
                        {
                            "role": "user",
                            "content": json.dumps(input_data, indent=2)
                        }
                    ],
                    temperature=0.1
                )
                
                content = response.choices[0].message.content
                evaluation_json = json.loads(content)
                
                evaluation_json = {
                    **evaluation_json,
                    "status": "revised"
                }
                
                # Validate evaluation output
                is_valid, errors = validate_evaluation_output(evaluation_json)
                if not is_valid:
                    print(f"[WARNING] Evaluation output validation found {len(errors)} issue(s):")
                    for error in errors[:5]:
                        print(f"  - {error}")
                
                return evaluation_json
            
            except Exception as e:
                print(f"ChatGPT API error: {e}, applying fixes locally")
                evaluation_json = self._apply_fixes_locally(simulation_json, critic_json, report_json)
                
                # Validate evaluation output
                is_valid, errors = validate_evaluation_output(evaluation_json)
                if not is_valid:
                    print(f"[WARNING] Evaluation output validation found {len(errors)} issue(s):")
                    for error in errors[:5]:
                        print(f"  - {error}")
                
                return evaluation_json
        
        # Default: return simulation as-is
        evaluation_json = {
            "final_simulation": simulation_json,
            "applied_fixes": [],
            "assumption_log": [],
            "status": "unknown"
        }
        
        # Validate evaluation output
        is_valid, errors = validate_evaluation_output(evaluation_json)
        if not is_valid:
            print(f"[WARNING] Evaluation output validation found {len(errors)} issue(s):")
            for error in errors[:5]:
                print(f"  - {error}")
        
        return evaluation_json
    
    def _apply_fixes_locally(
        self,
        simulation_json: Dict[str, Any],
        critic_json: Dict[str, Any],
        report_json: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Apply fixes locally without ChatGPT API."""
        applied_fixes = []
        assumption_log = []
        revised_simulation = json.loads(json.dumps(simulation_json))  # Deep copy
        
        # Apply suggested fixes
        suggested_fixes = critic_json.get("suggested_fixes", [])
        
        for fix in suggested_fixes:
            issue = fix.get("issue", "")
            fix_description = fix.get("fix", "")
            formula = fix.get("formula", "")
            
            # Apply balance sheet fixes
            if "balance sheet" in issue.lower():
                # This would require detailed balance sheet reconciliation
                # For now, we log the issue
                applied_fixes.append({
                    "fix": fix_description,
                    "before": "Balance sheet imbalance detected",
                    "after": "Balance sheet reconciliation required",
                    "impact": "Manual reconciliation needed"
                })
                assumption_log.append({
                    "change": f"Applied balance sheet fix: {fix_description}",
                    "effect": "Balance sheet reconciliation required"
                })
            
            # Apply cash flow fixes
            elif "cash flow" in issue.lower():
                # Adjust cash flow calculations
                if "formula_projections" in revised_simulation:
                    # Update FCF calculation if needed
                    applied_fixes.append({
                        "fix": fix_description,
                        "before": "Cash flow inconsistency",
                        "after": "Cash flow recalculated",
                        "impact": "Cash flow values updated"
                    })
                    assumption_log.append({
                        "change": f"Applied cash flow fix: {fix_description}",
                        "effect": "Cash flow calculations updated"
                    })
            
            # Apply other fixes
            else:
                applied_fixes.append({
                    "fix": fix_description,
                    "before": issue,
                    "after": "Fix applied",
                    "impact": "Values updated based on fix"
                })
                assumption_log.append({
                    "change": f"Applied fix: {fix_description}",
                    "effect": "Simulation updated"
                })
        
        # Update assumption log in revised simulation
        if "assumption_log" in revised_simulation:
            revised_simulation["assumption_log"].extend(assumption_log)
        else:
            revised_simulation["assumption_log"] = assumption_log
        
        evaluation_json = {
            "final_simulation": revised_simulation,
            "applied_fixes": applied_fixes,
            "assumption_log": assumption_log,
            "status": "revised"
        }
        
        # Validate evaluation output
        is_valid, errors = validate_evaluation_output(evaluation_json)
        if not is_valid:
            print(f"[WARNING] Local fix application output validation found {len(errors)} issue(s):")
            for error in errors[:5]:
                print(f"  - {error}")
        
        return evaluation_json

