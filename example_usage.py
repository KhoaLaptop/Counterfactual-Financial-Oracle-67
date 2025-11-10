"""
Example usage of the financial analysis pipeline.
"""

import asyncio
from src.ingestion import load_ade_json
from src.simulation import SimulationEngine
from src.critic import CriticEngine
from src.evaluator import EvaluatorEngine
from src.pdf_generator import PDFReportGenerator


async def example_usage():
    """Example of using the financial analysis pipeline."""
    
    # Load sample report
    print("Loading sample report...")
    report_json = load_ade_json("sample_data/sample_report.json")
    print("✓ Report loaded")
    
    # Define user controls (scenario deltas)
    user_controls = {
        "opex_delta_bps": -50,  # Reduce OpEx by 50 basis points (0.5%)
        "revenue_delta_bps": 0,  # No change to revenue
        "discount_rate_base": 0.08,  # 8% base discount rate
        "discount_rate_delta_bps": -200  # Reduce discount rate by 200 bps (2%)
    }
    
    print("\nUser Controls:")
    print(f"  OpEx Delta: {user_controls['opex_delta_bps']} bps")
    print(f"  Revenue Delta: {user_controls['revenue_delta_bps']} bps")
    print(f"  Discount Rate: {user_controls['discount_rate_base']*100:.2f}%")
    print(f"  Discount Rate Delta: {user_controls['discount_rate_delta_bps']} bps")
    
    # Step 1: Simulation
    print("\n" + "="*50)
    print("Step 1: Running Simulation")
    print("="*50)
    simulation_engine = SimulationEngine()
    simulation_json = await simulation_engine.run_simulation(report_json, user_controls)
    print("✓ Simulation complete")
    
    # Display simulation results
    if "formula_projections" in simulation_json:
        print("\nFormula Projections:")
        for metric, data in simulation_json["formula_projections"].items():
            if isinstance(data, dict):
                value = data.get("value", 0.0)
                formula = data.get("formula", "")
                print(f"  {metric.upper()}: ${value:,.2f}")
                print(f"    Formula: {formula}")
    
    if "monte_carlo" in simulation_json and "results" in simulation_json["monte_carlo"]:
        print("\nMonte Carlo Results (10,000 scenarios):")
        for metric, data in simulation_json["monte_carlo"]["results"].items():
            if isinstance(data, dict):
                median = data.get("median", 0.0)
                p10 = data.get("p10", 0.0)
                p90 = data.get("p90", 0.0)
                print(f"  {metric.upper().replace('_', ' ')}:")
                print(f"    Median: ${median:,.2f}")
                print(f"    10th Percentile: ${p10:,.2f}")
                print(f"    90th Percentile: ${p90:,.2f}")
    
    # Step 2: Critique
    print("\n" + "="*50)
    print("Step 2: Running Critique")
    print("="*50)
    critic_engine = CriticEngine()
    critic_json = await critic_engine.run_critique(report_json, simulation_json)
    print("✓ Critique complete")
    
    # Display critique results
    verdict = critic_json.get("verdict", "unknown")
    print(f"\nVerdict: {verdict.upper()}")
    
    if "constraint_checks" in critic_json:
        constraint_checks = critic_json["constraint_checks"]
        print("\nConstraint Checks:")
        
        if "balance_sheet" in constraint_checks:
            bs_check = constraint_checks["balance_sheet"]
            status = "✓ Balanced" if bs_check.get("is_balanced") else "✗ Imbalanced"
            print(f"  Balance Sheet: {status}")
            if not bs_check.get("is_balanced") and bs_check.get("error"):
                print(f"    Error: {bs_check['error']}")
        
        if "cash_flow" in constraint_checks:
            cf_check = constraint_checks["cash_flow"]
            status = "✓ Consistent" if cf_check.get("is_consistent") else "✗ Inconsistent"
            print(f"  Cash Flow: {status}")
            if not cf_check.get("is_consistent") and cf_check.get("error"):
                print(f"    Error: {cf_check['error']}")
    
    if "suggested_fixes" in critic_json:
        fixes = critic_json["suggested_fixes"]
        if fixes:
            print("\nSuggested Fixes:")
            for fix in fixes:
                print(f"  - {fix.get('issue', 'Unknown issue')}")
                print(f"    Fix: {fix.get('fix', 'Unknown fix')}")
    
    # Step 3: Evaluation
    print("\n" + "="*50)
    print("Step 3: Running Evaluation")
    print("="*50)
    evaluator_engine = EvaluatorEngine()
    evaluation_json = await evaluator_engine.evaluate(simulation_json, critic_json, report_json)
    print("✓ Evaluation complete")
    
    # Display evaluation results
    status = evaluation_json.get("status", "unknown")
    print(f"\nStatus: {status.upper()}")
    
    if "applied_fixes" in evaluation_json:
        applied_fixes = evaluation_json["applied_fixes"]
        if applied_fixes:
            print("\nApplied Fixes:")
            for fix in applied_fixes:
                print(f"  - {fix.get('fix', 'Unknown fix')}")
                print(f"    Impact: {fix.get('impact', 'Unknown impact')}")
    
    # Step 4: Generate PDF
    print("\n" + "="*50)
    print("Step 4: Generating PDF Report")
    print("="*50)
    pdf_generator = PDFReportGenerator()
    pdf_path = pdf_generator.generate_report(
        report_json, simulation_json, critic_json, evaluation_json, "example_output.pdf"
    )
    print(f"✓ PDF report generated: {pdf_path}")
    
    print("\n" + "="*50)
    print("Pipeline Complete!")
    print("="*50)
    
    return evaluation_json


if __name__ == "__main__":
    # Run the example
    asyncio.run(example_usage())

