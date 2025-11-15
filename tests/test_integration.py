"""
Integration tests for the full pipeline.
"""

import pytest
import asyncio
import json
from pathlib import Path
from src.ingestion import load_ade_json, validate_report_json
from src.validators import (
    validate_simulation_output,
    validate_critic_output,
    validate_evaluation_output,
    validate_user_controls
)


def create_minimal_report_json():
    """Create minimal valid report JSON for testing."""
    return {
        "income_statement": {
            "revenue": 1000000,
            "total_revenue": 1000000,
            "operating_expenses": 300000,
            "opex": 300000,
            "net_income": 315000,
            "ebitda": 500000,
            "ebit": 440000
        },
        "balance_sheet": {
            "assets": {"cash": 200000, "inventory": 300000},
            "liabilities": {"debt": 250000},
            "equity": {"equity": 250000},
            "total_assets": 500000
        },
        "cash_flow": {
            "cash_from_operations": 375000,
            "depreciation": 50000,
            "amortization": 10000,
            "capital_expenditures": 100000
        },
        "kpi_table": {
            "revenue": 1000000,
            "net_income": 315000,
            "ebitda": 500000
        },
        "industry_averages": {
            "ebitda_margin": 50.0,
            "net_margin": 31.5,
            "roa": 15.75
        },
        "index": {}
    }


def create_edge_case_report_json():
    """Create report JSON with edge case values."""
    return {
        "income_statement": {
            "revenue": 0,  # Zero revenue
            "total_revenue": 0,
            "operating_expenses": 0,
            "opex": 0,
            "net_income": -100000,  # Negative
            "ebitda": -100000
        },
        "balance_sheet": {
            "assets": {},
            "liabilities": {},
            "equity": {},
            "total_assets": 0
        },
        "cash_flow": {
            "cash_from_operations": 0,
            "depreciation": 0,
            "amortization": 0,
            "capital_expenditures": 0
        },
        "kpi_table": {},
        "industry_averages": {},
        "index": {}
    }


class TestPipelineIntegration:
    """Test full pipeline integration."""
    
    @pytest.mark.asyncio
    async def test_pipeline_with_sample_data(self):
        """Test complete pipeline with valid sample data."""
        # This test requires actual API keys, so we'll mock or skip if not available
        pytest.skip("Requires API keys - run manually or with mocks")
    
    def test_report_json_validation(self):
        """Test report JSON structure validation."""
        report_json = create_minimal_report_json()
        is_valid, errors = validate_report_json(report_json)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_report_json_validation_missing_sections(self):
        """Test report JSON validation with missing sections."""
        report_json = {
            "income_statement": {},
            # Missing balance_sheet and cash_flow
        }
        
        is_valid, errors = validate_report_json(report_json)
        assert is_valid is False
        assert len(errors) > 0
    
    def test_user_controls_validation(self):
        """Test user controls validation."""
        user_controls = {
            "opex_delta_bps": -50,
            "revenue_delta_bps": 0,
            "discount_rate_base": 0.08,
            "discount_rate_delta_bps": -200
        }
        
        is_valid, warnings = validate_user_controls(user_controls)
        assert is_valid is True
        assert len(warnings) == 0
    
    def test_user_controls_validation_extreme_values(self):
        """Test user controls validation with extreme values."""
        user_controls = {
            "opex_delta_bps": 5000,  # 50% - extreme
            "revenue_delta_bps": -3000,  # -30% - extreme
            "discount_rate_base": 0.08,
            "discount_rate_delta_bps": -200
        }
        
        is_valid, warnings = validate_user_controls(user_controls)
        # Should generate warnings for extreme values
        assert len(warnings) > 0


class TestOutputValidation:
    """Test output validation functions."""
    
    def test_validate_simulation_output_valid(self):
        """Test simulation output validation with valid data."""
        simulation_json = {
            "formula_projections": {
                "revenue": {"value": 1000000, "formula": "Revenue = Base * (1 + delta)"},
                "ebitda": {"value": 500000, "formula": "EBITDA = Revenue - OpEx"},
                "net_income": {"value": 315000, "formula": "Net Income = (EBIT - Interest) * (1 - Tax)"},
                "free_cash_flow": {"value": 255000, "formula": "FCF = Net Income + D&A - CapEx"},
                "npv": {"value": 1000000, "formula": "NPV = Σ(CF / (1+r)^t)"}
            },
            "monte_carlo": {
                "scenarios": 10000,
                "results": {
                    "revenue": {"median": 1000000, "p10": 900000, "p90": 1100000},
                    "ebitda": {"median": 500000, "p10": 450000, "p90": 550000},
                    "free_cash_flow": {"median": 255000, "p10": 200000, "p90": 300000},
                    "npv": {"median": 1000000, "p10": 800000, "p90": 1200000}
                }
            },
            "assumption_log": [
                {"transformation": "Applied -50 bps to OpEx", "before": 300000, "after": 298500}
            ]
        }
        
        is_valid, errors = validate_simulation_output(simulation_json)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_simulation_output_missing_fields(self):
        """Test simulation output validation with missing fields."""
        simulation_json = {
            "formula_projections": {
                "revenue": {"value": 1000000}
                # Missing other required metrics
            }
            # Missing monte_carlo and assumption_log
        }
        
        is_valid, errors = validate_simulation_output(simulation_json)
        assert is_valid is False
        assert len(errors) > 0
    
    def test_validate_simulation_output_invalid_percentiles(self):
        """Test simulation output validation with invalid percentile ordering."""
        simulation_json = {
            "formula_projections": {
                "revenue": {"value": 1000000, "formula": "Revenue = Base"},
                "ebitda": {"value": 500000, "formula": "EBITDA = Revenue - OpEx"},
                "net_income": {"value": 315000, "formula": "Net Income = ..."},
                "free_cash_flow": {"value": 255000, "formula": "FCF = ..."},
                "npv": {"value": 1000000, "formula": "NPV = ..."}
            },
            "monte_carlo": {
                "scenarios": 10000,
                "results": {
                    "revenue": {
                        "median": 900000,  # Median < p10 - invalid!
                        "p10": 1000000,
                        "p90": 1100000
                    }
                }
            },
            "assumption_log": []
        }
        
        is_valid, errors = validate_simulation_output(simulation_json)
        assert is_valid is False
        assert any("percentile ordering" in e.lower() for e in errors)
    
    def test_validate_simulation_output_nan_values(self):
        """Test simulation output validation with NaN values."""
        import math
        
        simulation_json = {
            "formula_projections": {
                "revenue": {"value": float('nan'), "formula": "Revenue = Base"},
                "ebitda": {"value": 500000, "formula": "EBITDA = Revenue - OpEx"},
                "net_income": {"value": 315000, "formula": "Net Income = ..."},
                "free_cash_flow": {"value": 255000, "formula": "FCF = ..."},
                "npv": {"value": 1000000, "formula": "NPV = ..."}
            },
            "monte_carlo": {
                "scenarios": 10000,
                "results": {
                    "revenue": {"median": 1000000, "p10": 900000, "p90": 1100000}
                }
            },
            "assumption_log": []
        }
        
        is_valid, errors = validate_simulation_output(simulation_json)
        assert is_valid is False
        assert any("nan" in e.lower() for e in errors)
    
    def test_validate_critic_output_approve(self):
        """Test critic output validation with approve verdict."""
        critic_json = {
            "verdict": "approve",
            "constraint_checks": {
                "balance_sheet": {"is_balanced": True, "error": None, "imbalance": 0.0},
                "cash_flow": {"is_consistent": True, "error": None, "difference": 0.0}
            },
            "suggested_fixes": []
        }
        
        is_valid, errors = validate_critic_output(critic_json)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_critic_output_revise(self):
        """Test critic output validation with revise verdict."""
        critic_json = {
            "verdict": "revise",
            "constraint_checks": {
                "balance_sheet": {"is_balanced": False, "error": "Imbalance detected", "imbalance": 10000.0},
                "cash_flow": {"is_consistent": True, "error": None, "difference": 0.0}
            },
            "suggested_fixes": [
                {"issue": "Balance sheet imbalance", "fix": "Adjust equity by $10,000"}
            ]
        }
        
        is_valid, errors = validate_critic_output(critic_json)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_critic_output_invalid_verdict(self):
        """Test critic output validation with invalid verdict."""
        critic_json = {
            "verdict": "maybe",  # Invalid
            "constraint_checks": {
                "balance_sheet": {"is_balanced": True},
                "cash_flow": {"is_consistent": True}
            }
        }
        
        is_valid, errors = validate_critic_output(critic_json)
        assert is_valid is False
        assert any("verdict" in e.lower() for e in errors)
    
    def test_validate_critic_output_revise_without_fixes(self):
        """Test critic output validation with revise but no fixes."""
        critic_json = {
            "verdict": "revise",
            "constraint_checks": {
                "balance_sheet": {"is_balanced": False},
                "cash_flow": {"is_consistent": True}
            },
            "suggested_fixes": []  # Empty but verdict is revise
        }
        
        is_valid, errors = validate_critic_output(critic_json)
        assert is_valid is False
        assert any("suggested_fixes" in e.lower() for e in errors)
    
    def test_validate_evaluation_output_approved(self):
        """Test evaluation output validation with approved status."""
        evaluation_json = {
            "status": "approved",
            "final_simulation": {
                "formula_projections": {
                    "revenue": {"value": 1000000, "formula": "Revenue = Base"}
                },
                "monte_carlo": {"results": {}},
                "assumption_log": []
            },
            "applied_fixes": []
        }
        
        is_valid, errors = validate_evaluation_output(evaluation_json)
        assert is_valid is True
    
    def test_validate_evaluation_output_revised(self):
        """Test evaluation output validation with revised status."""
        evaluation_json = {
            "status": "revised",
            "final_simulation": {
                "formula_projections": {
                    "revenue": {"value": 1000000, "formula": "Revenue = Base"}
                },
                "monte_carlo": {"results": {}},
                "assumption_log": []
            },
            "applied_fixes": [
                {"fix": "Adjusted balance sheet", "impact": "Fixed $10k imbalance"}
            ]
        }
        
        is_valid, errors = validate_evaluation_output(evaluation_json)
        assert is_valid is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

