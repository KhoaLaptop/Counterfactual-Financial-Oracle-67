"""
Streamlit app for financial analysis pipeline.
"""

import streamlit as st
import json
import asyncio
import os
from pathlib import Path
from typing import Dict, Any, Optional
import time
from datetime import datetime

from src.ingestion import (
    load_ade_json, 
    validate_report_json, 
    extract_kpis,
    extract_from_pdf_bytes,
    normalize_ade_response
)
from src.simulation import SimulationEngine
from src.critic import CriticEngine
from src.evaluator import EvaluatorEngine
from src.pdf_generator import PDFReportGenerator
from dotenv import load_dotenv

load_dotenv()

# Page config
st.set_page_config(
    page_title="Financial Analysis Pipeline",
    page_icon="📊",
    layout="wide"
)

# Initialize session state
if "report_json" not in st.session_state:
    st.session_state.report_json = None
if "simulation_json" not in st.session_state:
    st.session_state.simulation_json = None
if "critic_json" not in st.session_state:
    st.session_state.critic_json = None
if "evaluation_json" not in st.session_state:
    st.session_state.evaluation_json = None
if "debate_logs" not in st.session_state:
    st.session_state.debate_logs = []
if "processing" not in st.session_state:
    st.session_state.processing = False


def add_debate_log(role: str, message: str, data: Optional[Dict] = None):
    """Add a log entry to the debate logs."""
    log_entry = {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "role": role,
        "message": message,
        "data": data
    }
    st.session_state.debate_logs.append(log_entry)


async def run_pipeline(report_json: Dict[str, Any], user_controls: Dict[str, float]):
    """Run the complete analysis pipeline."""
    try:
        # Initialize engines
        simulation_engine = SimulationEngine()
        critic_engine = CriticEngine()
        evaluator_engine = EvaluatorEngine()
        
        # Step 1: Simulation
        add_debate_log("Simulation", "Starting formula-driven projections and Monte Carlo simulation...")
        simulation_json = await simulation_engine.run_simulation(report_json, user_controls)
        st.session_state.simulation_json = simulation_json
        add_debate_log("Simulation", "Simulation complete. Generated projections and 10,000 Monte Carlo scenarios.")
        
        # Step 2: Critic
        add_debate_log("Critic", "Starting forensic review of simulation results...")
        critic_json = await critic_engine.run_critique(report_json, simulation_json)
        st.session_state.critic_json = critic_json
        verdict = critic_json.get("verdict", "unknown")
        add_debate_log("Critic", f"Critique complete. Verdict: {verdict.upper()}")
        
        if verdict == "revise":
            fixes = critic_json.get("suggested_fixes", [])
            add_debate_log("Critic", f"Found {len(fixes)} issue(s) requiring revision.")
            for fix in fixes:
                add_debate_log("Critic", f"Issue: {fix.get('issue', 'Unknown')}", fix)
        
        # Step 3: Evaluator
        add_debate_log("Evaluator", "Evaluating critic feedback and applying fixes...")
        evaluation_json = await evaluator_engine.evaluate(simulation_json, critic_json, report_json)
        st.session_state.evaluation_json = evaluation_json
        status = evaluation_json.get("status", "unknown")
        add_debate_log("Evaluator", f"Evaluation complete. Status: {status.upper()}")
        
        applied_fixes = evaluation_json.get("applied_fixes", [])
        if applied_fixes:
            add_debate_log("Evaluator", f"Applied {len(applied_fixes)} fix(es).")
            for fix in applied_fixes:
                add_debate_log("Evaluator", f"Fix applied: {fix.get('fix', 'Unknown')}", fix)
        
        return True
    
    except Exception as e:
        add_debate_log("Error", f"Pipeline error: {str(e)}")
        st.error(f"Error running pipeline: {str(e)}")
        return False


def main():
    """Main Streamlit app."""
    st.title("📊 Financial Analysis Pipeline")
    st.markdown("""
    This application performs comprehensive financial analysis including:
    - Landing AI ADE JSON ingestion
    - OpenAI simulation with formula-driven projections and Monte Carlo (10k scenarios)
    - DeepSeek critic for forensic review
    - ChatGPT evaluator for applying fixes and generating final reports
    """)
    
    # Sidebar for file upload and controls
    with st.sidebar:
        st.header("📁 Data Input")
        
        # File upload - support both PDF and JSON
        upload_option = st.radio(
            "Upload type:",
            ["PDF File", "JSON File"],
            help="Upload a PDF file to extract data using Landing AI ADE, or upload a pre-extracted JSON file"
        )
        
        if upload_option == "PDF File":
            uploaded_file = st.file_uploader(
                "Upload PDF file",
                type=["pdf"],
                help="Upload a PDF file. Data will be extracted using Landing AI ADE API."
            )
            
            if uploaded_file is not None:
                if st.button("Extract Data from PDF", type="primary"):
                    with st.spinner("Extracting data from PDF using Landing AI ADE..."):
                        try:
                            # Read PDF bytes
                            pdf_bytes = uploaded_file.read()
                            filename = uploaded_file.name
                            
                            # Extract using Landing AI ADE API
                            ade_response = extract_from_pdf_bytes(pdf_bytes, filename)
                            
                            # Normalize response
                            report_json = normalize_ade_response(ade_response)
                            
                            # Check if we actually extracted any data
                            kpis = extract_kpis(report_json)
                            if not kpis or not any(kpis.values()):
                                st.warning("⚠️ Warning: No financial data could be extracted from the PDF.")
                                st.info("The PDF structure was recognized but no numeric values were found.")
                                st.json(ade_response)  # Show raw response for debugging
                            
                            st.session_state.report_json = report_json
                            
                            # Validate
                            is_valid, errors = validate_report_json(report_json)
                            if is_valid:
                                st.success("✓ Data extracted and validated")
                                if kpis:
                                    st.info(f"Extracted {len(kpis)} KPIs: {', '.join(list(kpis.keys())[:5])}...")
                            else:
                                st.warning(f"Extraction completed with warnings: {', '.join(errors)}")
                                st.info("You can still proceed, but some fields may be missing.")
                                # Show what was extracted
                                if kpis:
                                    with st.expander("View extracted data"):
                                        st.json(kpis)
                                else:
                                    st.error("No KPIs were extracted. Please check the PDF format or try uploading a JSON file instead.")
                        
                        except Exception as e:
                            st.error(f"Error extracting data from PDF: {str(e)}")
                            st.info("Make sure your Landing AI API key is set in the .env file")
            
            # Show current report if available
            if st.session_state.report_json is not None:
                st.success("✓ Report data loaded")
                if st.button("Clear Report"):
                    st.session_state.report_json = None
                    st.rerun()
        
        else:  # JSON File
            uploaded_file = st.file_uploader(
                "Upload Landing AI ADE JSON file",
                type=["json"],
                help="Upload a JSON file extracted from Landing AI ADE"
            )
            
            if uploaded_file is not None:
                try:
                    report_json = json.load(uploaded_file)
                    
                    # Check if data exists
                    kpis = extract_kpis(report_json)
                    if not kpis:
                        st.warning("⚠️ Warning: No KPIs found in JSON file.")
                        st.info("The JSON structure exists but no financial data was found.")
                        with st.expander("View JSON structure"):
                            st.json({k: type(v).__name__ for k, v in report_json.items()})
                    
                    st.session_state.report_json = report_json
                    
                    # Validate
                    is_valid, errors = validate_report_json(report_json)
                    if is_valid:
                        st.success("✓ Valid report JSON")
                        if kpis:
                            st.info(f"Found {len(kpis)} KPIs: {', '.join(list(kpis.keys())[:5])}...")
                    else:
                        st.error(f"Validation errors: {', '.join(errors)}")
                        if kpis:
                            with st.expander("View extracted KPIs"):
                                st.json(kpis)
                
                except json.JSONDecodeError:
                    st.error("Invalid JSON file")
                except Exception as e:
                    st.error(f"Error loading file: {str(e)}")
        
        st.divider()
        
        # Scenario controls
        st.header("⚙️ Scenario Controls")
        
        opex_delta = st.slider(
            "OpEx Delta (bps)",
            min_value=-500,
            max_value=500,
            value=0,
            step=10,
            help="Change in operating expenses in basis points (100 bps = 1%)"
        )
        
        revenue_delta = st.slider(
            "Revenue Delta (bps)",
            min_value=-500,
            max_value=500,
            value=0,
            step=10,
            help="Change in revenue in basis points"
        )
        
        discount_rate_base = st.slider(
            "Base Discount Rate (%)",
            min_value=0.0,
            max_value=20.0,
            value=8.0,
            step=0.1,
            help="Base discount rate for NPV calculations"
        )
        
        discount_rate_delta = st.slider(
            "Discount Rate Delta (bps)",
            min_value=-500,
            max_value=500,
            value=0,
            step=10,
            help="Change in discount rate in basis points"
        )
        
        user_controls = {
            "opex_delta_bps": opex_delta,
            "revenue_delta_bps": revenue_delta,
            "discount_rate_base": discount_rate_base / 100,
            "discount_rate_delta_bps": discount_rate_delta
        }
        
        st.divider()
        
        # Run analysis button
        if st.button("🚀 Run Analysis", type="primary", use_container_width=True):
            if st.session_state.report_json is None:
                st.error("Please upload a PDF or JSON file first")
            else:
                st.session_state.processing = True
                st.session_state.debate_logs = []
                
                # Run pipeline
                with st.spinner("Running analysis pipeline..."):
                    try:
                        success = asyncio.run(run_pipeline(st.session_state.report_json, user_controls))
                        st.session_state.processing = False
                        
                        if success:
                            st.success("Analysis complete!")
                            st.rerun()
                    except Exception as e:
                        st.session_state.processing = False
                        st.error(f"Analysis failed: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
    
    # Main content area
    tab1, tab2, tab3, tab4 = st.tabs(["📄 JSON Preview", "📊 Results", "💬 Debate Logs", "📥 Export"])
    
    # Tab 1: JSON Preview
    with tab1:
        st.header("Report Data Preview")
        if st.session_state.report_json:
            st.json(st.session_state.report_json)
            
            # Show KPIs
            st.subheader("Extracted KPIs")
            kpis = extract_kpis(st.session_state.report_json)
            if kpis:
                st.json(kpis)
            else:
                st.info("No KPIs found in report")
        else:
            st.info("Please upload a PDF or JSON file to see preview")
    
    # Tab 2: Results
    with tab2:
        st.header("Analysis Results")
        
        if st.session_state.simulation_json:
            st.subheader("Simulation Results")
            
            # Formula Projections
            if "formula_projections" in st.session_state.simulation_json:
                st.markdown("### Formula-Driven Projections")
                projections = st.session_state.simulation_json["formula_projections"]
                
                cols = st.columns(2)
                for idx, (metric, data) in enumerate(projections.items()):
                    with cols[idx % 2]:
                        if isinstance(data, dict):
                            value = data.get("value", 0.0)
                            formula = data.get("formula", "")
                            st.metric(metric.upper(), f"${value:,.2f}" if abs(value) >= 1 else f"{value:.4f}")
                            st.caption(f"Formula: {formula}")
            
            # Monte Carlo Results
            if "monte_carlo" in st.session_state.simulation_json and "results" in st.session_state.simulation_json["monte_carlo"]:
                st.markdown("### Monte Carlo Simulation Results")
                mc_results = st.session_state.simulation_json["monte_carlo"]["results"]
                
                mc_data = []
                for metric, data in mc_results.items():
                    if isinstance(data, dict):
                        mc_data.append({
                            "Metric": metric.upper().replace("_", " "),
                            "Median": f"${data.get('median', 0):,.2f}",
                            "10th Percentile": f"${data.get('p10', 0):,.2f}",
                            "90th Percentile": f"${data.get('p90', 0):,.2f}"
                        })
                
                if mc_data:
                    st.dataframe(mc_data, use_container_width=True)
        
        if st.session_state.critic_json:
            st.subheader("Critic Review")
            verdict = st.session_state.critic_json.get("verdict", "unknown")
            verdict_color = "green" if verdict == "approve" else "red"
            st.markdown(f"**Verdict:** :{verdict_color}[{verdict.upper()}]")
            
            # Constraint checks
            if "constraint_checks" in st.session_state.critic_json:
                constraint_checks = st.session_state.critic_json["constraint_checks"]
                
                if "balance_sheet" in constraint_checks:
                    bs_check = constraint_checks["balance_sheet"]
                    bs_status = "✓ Balanced" if bs_check.get("is_balanced") else "✗ Imbalanced"
                    st.write(f"Balance Sheet: {bs_status}")
                    if not bs_check.get("is_balanced") and bs_check.get("error"):
                        st.error(bs_check["error"])
                
                if "cash_flow" in constraint_checks:
                    cf_check = constraint_checks["cash_flow"]
                    cf_status = "✓ Consistent" if cf_check.get("is_consistent") else "✗ Inconsistent"
                    st.write(f"Cash Flow: {cf_status}")
                    if not cf_check.get("is_consistent") and cf_check.get("error"):
                        st.error(cf_check["error"])
            
            # Suggested fixes
            if "suggested_fixes" in st.session_state.critic_json:
                fixes = st.session_state.critic_json["suggested_fixes"]
                if fixes:
                    st.markdown("### Suggested Fixes")
                    for fix in fixes:
                        st.write(f"**Issue:** {fix.get('issue', 'Unknown')}")
                        st.write(f"**Fix:** {fix.get('fix', 'Unknown')}")
                        st.divider()
        
        if st.session_state.evaluation_json:
            st.subheader("Final Evaluation")
            status = st.session_state.evaluation_json.get("status", "unknown")
            st.markdown(f"**Status:** {status.upper()}")
            
            if "applied_fixes" in st.session_state.evaluation_json:
                applied_fixes = st.session_state.evaluation_json["applied_fixes"]
                if applied_fixes:
                    st.markdown("### Applied Fixes")
                    for fix in applied_fixes:
                        st.write(f"**Fix:** {fix.get('fix', 'Unknown')}")
                        st.write(f"**Impact:** {fix.get('impact', 'Unknown')}")
                        st.divider()
        else:
            st.info("Run analysis to see results")
    
    # Tab 3: Debate Logs
    with tab3:
        st.header("Real-time Debate Logs")
        
        if st.session_state.debate_logs:
            # Display logs in reverse order (newest first)
            for log in reversed(st.session_state.debate_logs):
                role = log.get("role", "Unknown")
                message = log.get("message", "")
                timestamp = log.get("timestamp", "")
                
                if role == "Simulation":
                    st.info(f"**[{timestamp}] Simulation:** {message}")
                elif role == "Critic":
                    st.warning(f"**[{timestamp}] Critic:** {message}")
                elif role == "Evaluator":
                    st.success(f"**[{timestamp}] Evaluator:** {message}")
                elif role == "Error":
                    st.error(f"**[{timestamp}] Error:** {message}")
                else:
                    st.write(f"**[{timestamp}] {role}:** {message}")
                
                if log.get("data"):
                    with st.expander("View details"):
                        st.json(log["data"])
        else:
            st.info("No debate logs yet. Run analysis to see real-time logs.")
        
        # Auto-refresh if processing
        if st.session_state.processing:
            time.sleep(1)
            st.rerun()
    
    # Tab 4: Export
    with tab4:
        st.header("Export Report")
        
        if (st.session_state.report_json and 
            st.session_state.simulation_json and 
            st.session_state.critic_json and 
            st.session_state.evaluation_json):
            
            if st.button("📄 Generate PDF Report", type="primary"):
                try:
                    pdf_generator = PDFReportGenerator()
                    
                    # Generate PDF to bytes directly
                    pdf_buffer = pdf_generator.generate_report_bytes(
                        st.session_state.report_json,
                        st.session_state.simulation_json,
                        st.session_state.critic_json,
                        st.session_state.evaluation_json
                    )
                    
                    pdf_bytes = pdf_buffer.read()
                    
                    st.download_button(
                        label="⬇️ Download PDF Report",
                        data=pdf_bytes,
                        file_name=f"financial_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf"
                    )
                    
                    st.success("PDF report generated successfully!")
                
                except Exception as e:
                    st.error(f"Error generating PDF: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
        else:
            st.info("Please run analysis first to generate PDF report")


if __name__ == "__main__":
    main()

