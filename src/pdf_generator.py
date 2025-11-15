"""
PDF generation module for final financial reports.
"""

from typing import Dict, List, Optional, Any
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
import json
import tempfile
import os
from datetime import datetime


class PDFReportGenerator:
    """PDF generator for financial analysis reports."""
    
    def __init__(self):
        """Initialize PDF generator."""
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        # Helper function to safely add styles
        def add_style_if_not_exists(name, style_obj):
            try:
                # Try to access the style - if it exists, this won't raise an error
                _ = self.styles[name]
                # If we get here, the style exists, so don't add it
            except KeyError:
                # Style doesn't exist, so add it
                self.styles.add(style_obj)
        
        # Add custom styles only if they don't exist
        add_style_if_not_exists('CustomTitle', ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        add_style_if_not_exists('SectionHeader', ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2c5aa0'),
            spaceAfter=12,
            spaceBefore=12
        ))
        
        # BodyText already exists in default stylesheet, so we create CustomBodyText
        add_style_if_not_exists('CustomBodyText', ParagraphStyle(
            name='CustomBodyText',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=14
        ))
    
    def generate_report(
        self,
        report_json: Dict[str, Any],
        simulation_json: Dict[str, Any],
        critic_json: Dict[str, Any],
        evaluation_json: Dict[str, Any],
        output_path: str
    ) -> str:
        """
        Generate PDF report from analysis results.
        
        Args:
            report_json: Original report JSON
            simulation_json: Simulation results
            critic_json: Critique results
            evaluation_json: Evaluation results
            output_path: Path to save PDF
        
        Returns:
            Path to generated PDF
        """
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        story = self._build_story(report_json, simulation_json, critic_json, evaluation_json)
        doc.build(story)
        return output_path
    
    def generate_report_bytes(
        self,
        report_json: Dict[str, Any],
        simulation_json: Dict[str, Any],
        critic_json: Dict[str, Any],
        evaluation_json: Dict[str, Any]
    ) -> BytesIO:
        """
        Generate PDF report as bytes.
        
        Args:
            report_json: Original report JSON
            simulation_json: Simulation results
            critic_json: Critique results
            evaluation_json: Evaluation results
        
        Returns:
            BytesIO object containing PDF
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = self._build_story(report_json, simulation_json, critic_json, evaluation_json)
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    def _build_story(
        self,
        report_json: Dict[str, Any],
        simulation_json: Dict[str, Any],
        critic_json: Dict[str, Any],
        evaluation_json: Dict[str, Any]
    ) -> List:
        """Build the story (content) for the PDF report."""
        story = []
        
        # Title
        story.append(Paragraph("Financial Analysis Report", self.styles['CustomTitle']))
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                              self.styles.get('CustomBodyText', self.styles['Normal'])))
        story.append(Spacer(1, 0.3*inch))
        
        # Executive Summary
        story.append(Paragraph("Executive Summary", self.styles['SectionHeader']))
        final_simulation = evaluation_json.get("final_simulation", simulation_json)
        verdict = critic_json.get("verdict", "unknown")
        
        summary_text = f"""
        This report presents a comprehensive financial analysis including formula-driven projections, 
        Monte Carlo simulation (10,000 scenarios), and rigorous validation. The analysis has been 
        reviewed by an automated critic system with a verdict of: <b>{verdict.upper()}</b>.
        """
        story.append(Paragraph(summary_text, self.styles.get('CustomBodyText', self.styles['Normal'])))
        story.append(Spacer(1, 0.2*inch))
        
        # Formula Projections
        story.append(Paragraph("Formula-Driven Projections", self.styles['SectionHeader']))
        if "formula_projections" in final_simulation:
            projections = final_simulation["formula_projections"]
            projection_data = [["Metric", "Value", "Formula"]]
            
            for metric, data in projections.items():
                if isinstance(data, dict):
                    value = data.get("value", 0.0)
                    formula = data.get("formula", "")
                    if isinstance(value, (int, float)):
                        value_str = f"${value:,.2f}" if abs(value) >= 1 else f"{value:.4f}"
                    else:
                        value_str = str(value)
                    projection_data.append([metric.upper(), value_str, formula])
            
            projection_table = Table(projection_data, colWidths=[2*inch, 2*inch, 3*inch])
            projection_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(projection_table)
            story.append(Spacer(1, 0.3*inch))
        
        # Monte Carlo Results
        story.append(Paragraph("Monte Carlo Simulation Results", self.styles['SectionHeader']))
        if "monte_carlo" in final_simulation and "results" in final_simulation["monte_carlo"]:
            mc_results = final_simulation["monte_carlo"]["results"]
            mc_data = [["Metric", "Median", "10th Percentile", "90th Percentile"]]
            
            for metric, data in mc_results.items():
                if isinstance(data, dict):
                    median = data.get("median", 0.0)
                    p10 = data.get("p10", 0.0)
                    p90 = data.get("p90", 0.0)
                    mc_data.append([
                        metric.upper().replace("_", " "),
                        f"${median:,.2f}",
                        f"${p10:,.2f}",
                        f"${p90:,.2f}"
                    ])
            
            mc_table = Table(mc_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
            mc_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(mc_table)
            story.append(Spacer(1, 0.3*inch))
        
        # Assumption Log
        story.append(Paragraph("Assumption Log", self.styles['SectionHeader']))
        if "assumption_log" in final_simulation:
            assumption_log = final_simulation["assumption_log"]
            for i, assumption in enumerate(assumption_log, 1):
                if isinstance(assumption, dict):
                    transformation = assumption.get("transformation", "")
                    impact = assumption.get("impact", "")
                    assumption_text = f"<b>{i}. {transformation}</b><br/>{impact}"
                    story.append(Paragraph(assumption_text, self.styles.get('CustomBodyText', self.styles['Normal'])))
                    story.append(Spacer(1, 0.1*inch))
        story.append(Spacer(1, 0.3*inch))
        
        # Critic Review
        story.append(Paragraph("Critic Review", self.styles['SectionHeader']))
        verdict_text = f"Verdict: <b>{critic_json.get('verdict', 'unknown').upper()}</b>"
        story.append(Paragraph(verdict_text, self.styles.get('CustomBodyText', self.styles['Normal'])))
        story.append(Spacer(1, 0.1*inch))
        
        # Constraint Checks
        if "constraint_checks" in critic_json:
            constraint_checks = critic_json["constraint_checks"]
            if "balance_sheet" in constraint_checks:
                bs_check = constraint_checks["balance_sheet"]
                bs_status = "✓ Balanced" if bs_check.get("is_balanced") else "✗ Imbalanced"
                story.append(Paragraph(f"Balance Sheet: {bs_status}", self.styles.get('CustomBodyText', self.styles['Normal'])))
                if not bs_check.get("is_balanced") and bs_check.get("error"):
                    story.append(Paragraph(bs_check["error"], self.styles.get('CustomBodyText', self.styles['Normal'])))
            
            if "cash_flow" in constraint_checks:
                cf_check = constraint_checks["cash_flow"]
                cf_status = "✓ Consistent" if cf_check.get("is_consistent") else "✗ Inconsistent"
                story.append(Paragraph(f"Cash Flow: {cf_status}", self.styles.get('CustomBodyText', self.styles['Normal'])))
                if not cf_check.get("is_consistent") and cf_check.get("error"):
                    story.append(Paragraph(cf_check["error"], self.styles.get('CustomBodyText', self.styles['Normal'])))
        
        story.append(Spacer(1, 0.3*inch))
        
        # Applied Fixes
        if evaluation_json.get("applied_fixes"):
            story.append(Paragraph("Applied Fixes", self.styles['SectionHeader']))
            for fix in evaluation_json["applied_fixes"]:
                if isinstance(fix, dict):
                    fix_text = f"<b>{fix.get('fix', '')}</b><br/>{fix.get('impact', '')}"
                    story.append(Paragraph(fix_text, self.styles.get('CustomBodyText', self.styles['Normal'])))
                    story.append(Spacer(1, 0.1*inch))
        
        # Appendix: Key Inputs and Document Sources
        story.append(PageBreak())
        story.append(Paragraph("Appendix: Key Inputs and Document Sources", self.styles['SectionHeader']))
        story.append(Spacer(1, 0.2*inch))
        
        # Extract key inputs from report_json
        story.append(Paragraph("Key Financial Inputs", self.styles.get('CustomBodyText', self.styles['Normal'])))
        story.append(Spacer(1, 0.1*inch))
        
        income_statement = report_json.get("income_statement", {})
        key_inputs = []
        
        if income_statement.get("revenue") or income_statement.get("total_revenue"):
            revenue = income_statement.get("revenue") or income_statement.get("total_revenue", 0)
            key_inputs.append(["Revenue", f"${revenue:,.2f}"])
        
        if income_statement.get("opex") or income_statement.get("operating_expenses"):
            opex = income_statement.get("opex") or income_statement.get("operating_expenses", 0)
            key_inputs.append(["Operating Expenses", f"${opex:,.2f}"])
        
        if income_statement.get("cogs") or income_statement.get("cost_of_goods_sold"):
            cogs = income_statement.get("cogs") or income_statement.get("cost_of_goods_sold", 0)
            key_inputs.append(["Cost of Goods Sold", f"${cogs:,.2f}"])
        
        if income_statement.get("net_income"):
            net_income = income_statement.get("net_income", 0)
            key_inputs.append(["Net Income", f"${net_income:,.2f}"])
        
        if key_inputs:
            inputs_table = Table([["Input", "Value"]] + key_inputs, colWidths=[3*inch, 2*inch])
            inputs_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(inputs_table)
            story.append(Spacer(1, 0.3*inch))
        
        # Document Sources
        story.append(Paragraph("Document Sources (ADE Extraction)", self.styles.get('CustomBodyText', self.styles['Normal'])))
        story.append(Spacer(1, 0.1*inch))
        
        index = report_json.get("index", {})
        if index:
            source_data = [["Field", "Source", "Method", "Location", "Original Text"]]
            
            for field_key, source_info in list(index.items())[:20]:  # Limit to first 20 for PDF
                source = source_info.get("source", "Unknown")
                method = source_info.get("extraction_method", "unknown")
                location = ""
                if "table_index" in source_info and "row_index" in source_info:
                    location = f"Table {source_info['table_index']}, Row {source_info['row_index']}"
                elif "page" in source_info:
                    location = f"Page {source_info['page']}"
                
                original_text = source_info.get("original_text", "")[:50]  # First 50 chars
                if len(source_info.get("original_text", "")) > 50:
                    original_text += "..."
                
                source_data.append([
                    field_key,
                    source,
                    method.replace("_", " ").title(),
                    location,
                    original_text
                ])
            
            if len(index) > 20:
                source_data.append([
                    f"... and {len(index) - 20} more fields",
                    "", "", "", ""
                ])
            
            sources_table = Table(source_data, colWidths=[1.5*inch, 1*inch, 1*inch, 1.2*inch, 2.3*inch])
            sources_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP')
            ]))
            story.append(sources_table)
        else:
            story.append(Paragraph(
                "No source tracking information available. Fields may have been loaded from JSON without ADE extraction.",
                self.styles.get('CustomBodyText', self.styles['Normal'])
            ))
        
        return story

