"""
Main entry point for the financial analysis pipeline.
Can be used as a CLI tool or imported as a module.
"""

import asyncio
import json
import sys
from pathlib import Path
from src.ingestion import load_ade_json
from src.simulation import SimulationEngine
from src.critic import CriticEngine
from src.evaluator import EvaluatorEngine
from src.pdf_generator import PDFReportGenerator


async def run_pipeline_cli(
    report_path: str,
    output_path: str = "output.pdf",
    opex_delta_bps: float = 0.0,
    revenue_delta_bps: float = 0.0,
    discount_rate_base: float = 0.08,
    discount_rate_delta_bps: float = 0.0
):
    """
    Run the financial analysis pipeline from command line.
    
    Args:
        report_path: Path to Landing AI ADE JSON file
        output_path: Path to output PDF file
        opex_delta_bps: OpEx delta in basis points
        revenue_delta_bps: Revenue delta in basis points
        discount_rate_base: Base discount rate (as decimal)
        discount_rate_delta_bps: Discount rate delta in basis points
    """
    print("Loading report JSON...")
    report_json = load_ade_json(report_path)
    print("✓ Report loaded")
    
    user_controls = {
        "opex_delta_bps": opex_delta_bps,
        "revenue_delta_bps": revenue_delta_bps,
        "discount_rate_base": discount_rate_base,
        "discount_rate_delta_bps": discount_rate_delta_bps
    }
    
    print("Running simulation...")
    simulation_engine = SimulationEngine()
    simulation_json = await simulation_engine.run_simulation(report_json, user_controls)
    print("✓ Simulation complete")
    
    print("Running critique...")
    critic_engine = CriticEngine()
    critic_json = await critic_engine.run_critique(report_json, simulation_json)
    print(f"✓ Critique complete (verdict: {critic_json.get('verdict', 'unknown')})")
    
    print("Running evaluation...")
    evaluator_engine = EvaluatorEngine()
    evaluation_json = await evaluator_engine.evaluate(simulation_json, critic_json, report_json)
    print("✓ Evaluation complete")
    
    print("Generating PDF report...")
    pdf_generator = PDFReportGenerator()
    pdf_path = pdf_generator.generate_report(
        report_json, simulation_json, critic_json, evaluation_json, output_path
    )
    print(f"✓ PDF report generated: {pdf_path}")
    
    return evaluation_json


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python main.py <report_json_path> [output_pdf_path] [options]")
        print("\nOptions:")
        print("  --opex-delta-bps <value>      OpEx delta in basis points (default: 0)")
        print("  --revenue-delta-bps <value>   Revenue delta in basis points (default: 0)")
        print("  --discount-rate-base <value>  Base discount rate as decimal (default: 0.08)")
        print("  --discount-rate-delta-bps <value>  Discount rate delta in basis points (default: 0)")
        print("\nExample:")
        print("  python main.py sample_data/sample_report.json output.pdf --opex-delta-bps -50")
        sys.exit(1)
    
    report_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "output.pdf"
    
    # Parse options
    opex_delta_bps = 0.0
    revenue_delta_bps = 0.0
    discount_rate_base = 0.08
    discount_rate_delta_bps = 0.0
    
    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == "--opex-delta-bps" and i + 1 < len(sys.argv):
            opex_delta_bps = float(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--revenue-delta-bps" and i + 1 < len(sys.argv):
            revenue_delta_bps = float(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--discount-rate-base" and i + 1 < len(sys.argv):
            discount_rate_base = float(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--discount-rate-delta-bps" and i + 1 < len(sys.argv):
            discount_rate_delta_bps = float(sys.argv[i + 1])
            i += 2
        else:
            i += 1
    
    # Run pipeline
    try:
        asyncio.run(run_pipeline_cli(
            report_path, output_path, opex_delta_bps, revenue_delta_bps,
            discount_rate_base, discount_rate_delta_bps
        ))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

