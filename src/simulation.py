"""
OpenAI simulation module with formula-driven projections and Monte Carlo simulation.
"""

import os
import json
import asyncio
from typing import Dict, List, Optional, Any
from openai import OpenAI
from dotenv import load_dotenv
import numpy as np

from .financial_formulas import (
    calculate_ebitda,
    calculate_ebit,
    calculate_net_income,
    calculate_free_cash_flow,
    calculate_npv,
    apply_delta_percentage,
    calculate_percentiles,
    monte_carlo_simulation
)
from .ingestion import extract_kpis, get_field_reference

load_dotenv()


SIMULATION_PROMPT = """You are a professional financial analyst and quantitative financial modeller. You will receive:

- `report_json`: the extracted JSON from Landing AI ADE, with structured fields (income_statement, balance_sheet, cash_flow, notes, KPI table, & an index mapping each field back to the original document section or page).

- `user_controls`: scenario deltas (e.g., OpEx delta = -50 bps, discount_rate delta = -200 bps).

Your tasks (strictly):

1) Formula-driven projections
   - Use exact KPIs from `report_json` to compute derived metrics via formulas (show formulas explicitly).
   - Example: if OpEx drops 50 bps, compute `OpEx_new = OpEx * (1 - 0.005)`, then `EBITDA = Revenue - OpEx_new`.
   - For each derived metric output the exact formula used and input numbers.

2) Monte Carlo simulation
   - Run **10,000** scenarios. Use the scenario deltas as parameters for distributions (default: normal unless another distribution is justified).
   - For each scenario compute projected P&L, cash flows, NPV (with supplied discount rate), and a short statement about the scenario's key driver(s).

3) Show your work
   - Output a structured `assumption_log` array describing each transformation, e.g.:
     "Applied −200 bps to discount rate (from 8.00% to 6.00%) → NPV changed from $X to $Y (Monte Carlo median)."
   - Provide median, 10th, 90th percentiles for key outputs (revenue, EBITDA, FCF, NPV).

4) Explainability / traceability
   - For each material input (revenue growth, margin, OpEx, capex, working capital), cite the `report_json` field and the document section (page/paragraph id) that supports using that baseline.
   - If you change a number, explain why and reference supporting text.

Return your response as a valid JSON object with the following structure:
{
  "formula_projections": {
    "revenue": {"value": ..., "formula": "...", "inputs": {...}},
    "ebitda": {"value": ..., "formula": "...", "inputs": {...}},
    "net_income": {"value": ..., "formula": "...", "inputs": {...}},
    "free_cash_flow": {"value": ..., "formula": "...", "inputs": {...}},
    "npv": {"value": ..., "formula": "...", "inputs": {...}}
  },
  "monte_carlo": {
    "scenarios": 10000,
    "results": {
      "revenue": {"median": ..., "p10": ..., "p90": ..., "distribution": [...]},
      "ebitda": {"median": ..., "p10": ..., "p90": ..., "distribution": [...]},
      "free_cash_flow": {"median": ..., "p10": ..., "p90": ..., "distribution": [...]},
      "npv": {"median": ..., "p10": ..., "p90": ..., "distribution": [...]}
    },
    "scenario_drivers": ["driver1", "driver2", ...]
  },
  "assumption_log": [
    {"transformation": "...", "before": ..., "after": ..., "impact": "..."},
    ...
  ],
  "traceability": [
    {"metric": "...", "source_field": "...", "source_section": "...", "justification": "..."},
    ...
  ]
}
"""


class SimulationEngine:
    """OpenAI simulation engine for financial projections."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize simulation engine.
        
        Args:
            api_key: OpenAI API key (default: from environment)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")
        
        self.client = OpenAI(api_key=self.api_key)
    
    async def run_simulation(
        self,
        report_json: Dict[str, Any],
        user_controls: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Run financial simulation with formula projections and Monte Carlo.
        
        Args:
            report_json: Report JSON from Landing AI ADE
            user_controls: Scenario deltas (e.g., {"opex_delta_bps": -50, "discount_rate_delta_bps": -200})
        
        Returns:
            Simulation results dictionary
        """
        # Prepare input for OpenAI
        input_data = {
            "report_json": report_json,
            "user_controls": user_controls
        }
        
        # Call OpenAI API
        try:
            # Try the custom API endpoint first (as per user's guide)
            try:
                print("[DEBUG] Attempting GPT-5-nano API call...")
                response = self.client.responses.create(
                    model="gpt-5-nano",
                    input=json.dumps(input_data),
                    store=True,
                )
                output_text = response.output_text
                simulation_json = json.loads(output_text)
                print("[DEBUG] GPT-5-nano API call successful")
            except (AttributeError, Exception) as e1:
                print(f"[DEBUG] GPT-5-nano failed: {e1}, trying standard API...")
                # Fallback to standard chat completion API
                try:
                    response = self.client.chat.completions.create(
                        model="gpt-4-turbo-preview",
                        messages=[
                            {
                                "role": "system",
                                "content": SIMULATION_PROMPT
                            },
                            {
                                "role": "user",
                                "content": json.dumps(input_data, indent=2)
                            }
                        ],
                        temperature=0.1
                    )
                    output_text = response.choices[0].message.content
                    # Try to extract JSON from response (might have markdown code blocks)
                    if "```json" in output_text:
                        output_text = output_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in output_text:
                        output_text = output_text.split("```")[1].split("```")[0].strip()
                    simulation_json = json.loads(output_text)
                    print("[DEBUG] Standard OpenAI API call successful")
                except Exception as e2:
                    print(f"[DEBUG] Standard API also failed: {e2}")
                    raise e2
            
            # Only enhance with local Monte Carlo if OpenAI didn't provide complete results
            monte_carlo = simulation_json.get("monte_carlo", {})
            results = monte_carlo.get("results", {})

            def _is_incomplete(results_dict: Dict[str, Any]) -> bool:
                if not results_dict:
                    return True
                required_metrics = ["revenue", "ebitda", "free_cash_flow", "npv"]
                for metric in required_metrics:
                    metric_data = results_dict.get(metric, {})
                    if not isinstance(metric_data, dict):
                        return True
                    median_val = metric_data.get("median")
                    if median_val is None:
                        return True
                return False

            if not monte_carlo or _is_incomplete(results):
                print("[DEBUG] OpenAI response missing Monte Carlo data, enhancing with local simulation...")
                simulation_json = await self._enhance_with_local_monte_carlo(
                    report_json, user_controls, simulation_json
                )
            else:
                print("[DEBUG] Using OpenAI Monte Carlo results directly")
            
            # Ensure required formula projections exist; fill from local simulation if missing
            required_metrics = ["revenue", "ebitda", "net_income", "free_cash_flow", "npv"]

            def _projection_missing(proj_dict: Dict[str, Any], item: str) -> bool:
                entry = proj_dict.get(item)
                if not isinstance(entry, dict):
                    return True
                value = entry.get("value")
                return not isinstance(value, (int, float))

            formula_projections = simulation_json.setdefault("formula_projections", {})
            missing_metrics = [
                metric for metric in required_metrics if _projection_missing(formula_projections, metric)
            ]

            if missing_metrics:
                print(f"[DEBUG] Formula projections missing metrics {missing_metrics}, computing locally...")
                try:
                    local_simulation = await self._run_local_simulation(report_json, user_controls)
                    local_fp = local_simulation.get("formula_projections", {})
                    for metric in missing_metrics:
                        if isinstance(local_fp.get(metric), dict):
                            formula_projections[metric] = local_fp[metric]

                    local_mc = local_simulation.get("monte_carlo")
                    if local_mc and _is_incomplete(simulation_json.get("monte_carlo", {}).get("results", {})):
                        simulation_json["monte_carlo"] = local_mc
                except Exception as local_err:
                    print(f"[WARNING] Unable to supplement formula projections locally: {local_err}")
            
            return simulation_json
        
        except Exception as e:
            # Fallback to local simulation if API fails
            print(f"[WARNING] OpenAI API error: {e}")
            print(f"[INFO] Falling back to local simulation using report data...")
            return await self._run_local_simulation(report_json, user_controls)
    
    async def _enhance_with_local_monte_carlo(
        self,
        report_json: Dict[str, Any],
        user_controls: Dict[str, float],
        simulation_json: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhance simulation results with local Monte Carlo validation."""
        kpis = extract_kpis(report_json)
        
        # Ensure monte_carlo section exists
        if "monte_carlo" not in simulation_json:
            simulation_json["monte_carlo"] = {"scenarios": 10000, "results": {}}
        
        # Run local Monte Carlo for key metrics
        num_scenarios = 10000
        base_revenue = kpis.get("revenue", kpis.get("total_revenue", 1000000))
        base_opex = kpis.get("opex", kpis.get("operating_expenses", base_revenue * 0.3))
        
        # Apply deltas
        opex_delta_bps = user_controls.get("opex_delta_bps", 0.0)
        revenue_delta_bps = user_controls.get("revenue_delta_bps", 0.0)
        
        adjusted_revenue = apply_delta_percentage(base_revenue, revenue_delta_bps)
        adjusted_opex = apply_delta_percentage(base_opex, opex_delta_bps)
        
        # Generate scenarios
        revenue_scenarios = monte_carlo_simulation(
            adjusted_revenue, num_scenarios, 
            mean_delta=revenue_delta_bps / 10000,
            std_delta=0.02
        )
        
        opex_scenarios = monte_carlo_simulation(
            adjusted_opex, num_scenarios,
            mean_delta=opex_delta_bps / 10000,
            std_delta=0.015
        )
        
        # Calculate EBITDA scenarios
        ebitda_scenarios = [
            calculate_ebitda(rev, opex) 
            for rev, opex in zip(revenue_scenarios, opex_scenarios)
        ]
        
        # Calculate FCF scenarios
        depreciation = kpis.get("depreciation", 0.0)
        amortization = kpis.get("amortization", 0.0)
        capex = kpis.get("capex", kpis.get("capital_expenditures", 0.0))
        net_income_base = kpis.get("net_income", adjusted_revenue * 0.1)
        
        fcf_scenarios = [
            calculate_free_cash_flow(
                net_income_base * (rev / adjusted_revenue),
                depreciation,
                amortization,
                capex
            )
            for rev in revenue_scenarios
        ]
        
        # Calculate NPV scenarios
        discount_rate_base = user_controls.get("discount_rate_base", 0.08)
        discount_rate_delta_bps = user_controls.get("discount_rate_delta_bps", 0.0)
        discount_rate = discount_rate_base + (discount_rate_delta_bps / 10000)
        
        npv_scenarios = [
            calculate_npv([fcf] * 5, discount_rate)
            for fcf in fcf_scenarios
        ]
        
        # Update simulation JSON with local results
        simulation_json["monte_carlo"]["results"]["revenue"] = {
            "median": np.median(revenue_scenarios),
            "p10": np.percentile(revenue_scenarios, 10),
            "p90": np.percentile(revenue_scenarios, 90),
            "distribution": revenue_scenarios[:100]  # Sample for storage
        }
        
        simulation_json["monte_carlo"]["results"]["ebitda"] = {
            "median": np.median(ebitda_scenarios),
            "p10": np.percentile(ebitda_scenarios, 10),
            "p90": np.percentile(ebitda_scenarios, 90),
            "distribution": ebitda_scenarios[:100]
        }
        
        simulation_json["monte_carlo"]["results"]["free_cash_flow"] = {
            "median": np.median(fcf_scenarios),
            "p10": np.percentile(fcf_scenarios, 10),
            "p90": np.percentile(fcf_scenarios, 90),
            "distribution": fcf_scenarios[:100]
        }
        
        simulation_json["monte_carlo"]["results"]["npv"] = {
            "median": np.median(npv_scenarios),
            "p10": np.percentile(npv_scenarios, 10),
            "p90": np.percentile(npv_scenarios, 90),
            "distribution": npv_scenarios[:100]
        }
        
        return simulation_json
    
    async def _run_local_simulation(
        self,
        report_json: Dict[str, Any],
        user_controls: Dict[str, float]
    ) -> Dict[str, Any]:
        """Run local simulation without OpenAI API."""
        kpis = extract_kpis(report_json)
        
        # Log extracted KPIs for debugging
        print(f"[DEBUG] Extracted KPIs: {list(kpis.keys())}")
        if kpis:
            sample_kpis = {k: f"{v:,.2f}" if isinstance(v, (int, float)) else str(v) 
                          for k, v in list(kpis.items())[:5]}
            print(f"[DEBUG] Sample KPI values: {sample_kpis}")
        
        # Extract base values with better fallback handling
        # Try multiple possible field names and sources
        base_revenue = None
        for key in ["revenue", "total_revenue"]:
            if key in kpis and kpis[key] is not None:
                base_revenue = float(kpis[key])
                break
        if base_revenue is None:
            is_data = report_json.get("income_statement", {})
            for key in ["revenue", "total_revenue"]:
                if key in is_data and is_data[key] is not None:
                    base_revenue = float(is_data[key])
                    break
        if base_revenue is None:
            kpi_table = report_json.get("kpi_table", {})
            if isinstance(kpi_table, dict):
                for key in ["revenue", "total_revenue"]:
                    if key in kpi_table and kpi_table[key] is not None:
                        base_revenue = float(kpi_table[key])
                        break
        
        if base_revenue is None or base_revenue == 0:
            # Provide detailed diagnostic information
            is_data = report_json.get('income_statement', {})
            kpi_table = report_json.get('kpi_table', {})
            
            # Check if structures are empty
            is_empty = isinstance(is_data, dict) and len(is_data) == 0
            kpi_empty = isinstance(kpi_table, dict) and len(kpi_table) == 0
            
            error_msg = (
                f"❌ Cannot find revenue in report.\n\n"
                f"**Diagnostic Information:**\n"
                f"- Report has structure: {list(report_json.keys())}\n"
                f"- Extracted KPIs: {list(kpis.keys()) if kpis else 'None (empty)'}\n"
                f"- Income statement: {'Empty dictionary {}' if is_empty else f'Has {len(is_data)} keys: {list(is_data.keys())[:5]}'}\n"
                f"- KPI table: {'Empty dictionary {}' if kpi_empty else f'Has {len(kpi_table)} keys: {list(kpi_table.keys())[:5]}'}\n\n"
                f"**Possible Issues:**\n"
                f"1. The JSON file has the structure but no data values (empty dictionaries)\n"
                f"2. Revenue field is missing or has a different name\n"
                f"3. Data values are not numeric (might be strings)\n\n"
                f"**Solution:**\n"
                f"Please ensure your JSON file has at least one of these fields with a numeric value:\n"
                f"- income_statement.revenue\n"
                f"- income_statement.total_revenue\n"
                f"- kpi_table.revenue\n"
                f"- kpi_table.total_revenue\n\n"
                f"See EXPECTED_FORMAT.md for the expected JSON format.\n"
                f"Or use the sample file: sample_data/sample_report.json"
            )
            raise ValueError(error_msg)
        
        # Extract other values (0.0 is valid for these, so we check for None)
        def safe_get_float(data, *keys, default=None):
            for key in keys:
                if key in data and data[key] is not None:
                    try:
                        val = float(data[key])
                        return val  # Return even if 0.0
                    except (ValueError, TypeError):
                        continue
            return default
        
        # Try to get opex from multiple sources
        base_opex = safe_get_float(kpis, "opex", "operating_expenses")
        if base_opex is None:
            base_opex = safe_get_float(report_json.get("income_statement", {}), "opex", "operating_expenses")
        if base_opex is None:
            base_opex = base_revenue * 0.3  # Fallback: assume 30% of revenue
        
        base_cogs = safe_get_float(kpis, "cogs", "cost_of_goods_sold")
        if base_cogs is None:
            base_cogs = safe_get_float(report_json.get("income_statement", {}), "cogs", "cost_of_goods_sold", default=0.0)
        
        depreciation = safe_get_float(kpis, "depreciation")
        if depreciation is None:
            depreciation = safe_get_float(report_json.get("income_statement", {}), "depreciation")
        if depreciation is None:
            depreciation = safe_get_float(report_json.get("cash_flow", {}), "depreciation", default=0.0)
        
        amortization = safe_get_float(kpis, "amortization")
        if amortization is None:
            amortization = safe_get_float(report_json.get("income_statement", {}), "amortization")
        if amortization is None:
            amortization = safe_get_float(report_json.get("cash_flow", {}), "amortization", default=0.0)
        
        capex = safe_get_float(kpis, "capex", "capital_expenditures")
        if capex is None:
            capex = safe_get_float(report_json.get("cash_flow", {}), "capex", "capital_expenditures", default=0.0)
        
        net_income_base = safe_get_float(kpis, "net_income")
        if net_income_base is None:
            net_income_base = safe_get_float(report_json.get("income_statement", {}), "net_income")
        if net_income_base is None:
            net_income_base = base_revenue * 0.1  # Fallback: assume 10% margin
        
        print(f"[DEBUG] Using base_revenue: {base_revenue:,.2f}")
        print(f"[DEBUG] Using base_opex: {base_opex:,.2f}")
        print(f"[DEBUG] Using net_income_base: {net_income_base:,.2f}")
        
        # Apply deltas
        opex_delta_bps = user_controls.get("opex_delta_bps", 0.0)
        revenue_delta_bps = user_controls.get("revenue_delta_bps", 0.0)
        discount_rate_base = user_controls.get("discount_rate_base", 0.08)
        discount_rate_delta_bps = user_controls.get("discount_rate_delta_bps", 0.0)
        
        adjusted_revenue = apply_delta_percentage(base_revenue, revenue_delta_bps)
        adjusted_opex = apply_delta_percentage(base_opex, opex_delta_bps)
        discount_rate = discount_rate_base + (discount_rate_delta_bps / 10000)
        
        # Formula projections
        ebitda = calculate_ebitda(adjusted_revenue, adjusted_opex, base_cogs)
        ebit = calculate_ebit(ebitda, depreciation, amortization)
        tax_rate = kpis.get("tax_rate", 0.25)
        interest_expense = kpis.get("interest_expense", 0.0)
        net_income = calculate_net_income(ebit, interest_expense, tax_rate)
        fcf = calculate_free_cash_flow(net_income, depreciation, amortization, capex)
        npv = calculate_npv([fcf] * 5, discount_rate)
        
        formula_projections = {
            "revenue": {
                "value": adjusted_revenue,
                "formula": f"Revenue = Base Revenue * (1 + {revenue_delta_bps}/10000)",
                "inputs": {"base_revenue": base_revenue, "revenue_delta_bps": revenue_delta_bps}
            },
            "ebitda": {
                "value": ebitda,
                "formula": "EBITDA = Revenue - COGS - OpEx",
                "inputs": {"revenue": adjusted_revenue, "cogs": base_cogs, "opex": adjusted_opex}
            },
            "net_income": {
                "value": net_income,
                "formula": "Net Income = (EBIT - Interest Expense) * (1 - Tax Rate)",
                "inputs": {"ebit": ebit, "interest_expense": interest_expense, "tax_rate": tax_rate}
            },
            "free_cash_flow": {
                "value": fcf,
                "formula": "FCF = Net Income + D&A - CapEx - ΔWC",
                "inputs": {"net_income": net_income, "depreciation": depreciation, 
                          "amortization": amortization, "capex": capex}
            },
            "npv": {
                "value": npv,
                "formula": f"NPV = Σ(CF / (1 + r)^t) where r = {discount_rate}",
                "inputs": {"cash_flows": [fcf] * 5, "discount_rate": discount_rate}
            }
        }
        
        # Run Monte Carlo
        await self._enhance_with_local_monte_carlo(report_json, user_controls, {
            "formula_projections": formula_projections,
            "monte_carlo": {"scenarios": 10000, "results": {}},
            "assumption_log": [],
            "traceability": []
        })
        
        simulation_json = await self._enhance_with_local_monte_carlo(
            report_json, user_controls, {
                "formula_projections": formula_projections,
                "monte_carlo": {"scenarios": 10000, "results": {}},
                "assumption_log": [
                    {
                        "transformation": f"Applied {revenue_delta_bps} bps to revenue",
                        "before": base_revenue,
                        "after": adjusted_revenue,
                        "impact": f"Revenue changed by ${adjusted_revenue - base_revenue:,.2f}"
                    },
                    {
                        "transformation": f"Applied {opex_delta_bps} bps to OpEx",
                        "before": base_opex,
                        "after": adjusted_opex,
                        "impact": f"OpEx changed by ${adjusted_opex - base_opex:,.2f}"
                    },
                    {
                        "transformation": f"Applied {discount_rate_delta_bps} bps to discount rate",
                        "before": discount_rate_base,
                        "after": discount_rate,
                        "impact": f"Discount rate changed from {discount_rate_base*100:.2f}% to {discount_rate*100:.2f}%"
                    }
                ],
                "traceability": [
                    {
                        "metric": "revenue",
                        "source_field": "revenue" if "revenue" in kpis else "total_revenue",
                        "source_section": "income_statement",
                        "justification": "Base revenue from income statement"
                    }
                ]
            }
        )
        
        return simulation_json

