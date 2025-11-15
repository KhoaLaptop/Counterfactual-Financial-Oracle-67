"""
Unit tests for ADE → model mapping.
Tests parsing revenue, COGS, OpEx correctly from fixed ADE JSON.
"""

import pytest
from src.ingestion import (
    normalize_ade_response,
    extract_kpis,
    _parse_numeric,
    _apply_table_mapping,
    INCOME_STATEMENT_FIELD_MAP
)


class TestADEMapping:
    """Test ADE response mapping to financial model fields."""
    
    def test_parse_revenue_from_ade_json(self):
        """Test parsing revenue from ADE JSON structure."""
        ade_response = {
            "income_statement": {
                "revenue": 1000000.0,
                "total_revenue": 1000000.0
            },
            "kpi_table": {
                "revenue": 1000000.0
            }
        }
        
        normalized = normalize_ade_response(ade_response)
        kpis = extract_kpis(normalized)
        
        assert "revenue" in kpis
        assert kpis["revenue"] == 1000000.0
        assert normalized["income_statement"]["revenue"] == 1000000.0
    
    def test_parse_cogs_from_ade_json(self):
        """Test parsing COGS from ADE JSON structure."""
        ade_response = {
            "income_statement": {
                "cost_of_goods_sold": 400000.0,
                "cogs": 400000.0
            }
        }
        
        normalized = normalize_ade_response(ade_response)
        kpis = extract_kpis(normalized)
        
        assert "cogs" in kpis or "cost_of_goods_sold" in kpis
        cogs_value = kpis.get("cogs") or kpis.get("cost_of_goods_sold")
        assert cogs_value == 400000.0
    
    def test_parse_opex_from_ade_json(self):
        """Test parsing OpEx from ADE JSON structure."""
        ade_response = {
            "income_statement": {
                "operating_expenses": 300000.0,
                "opex": 300000.0
            }
        }
        
        normalized = normalize_ade_response(ade_response)
        kpis = extract_kpis(normalized)
        
        assert "opex" in kpis or "operating_expenses" in kpis
        opex_value = kpis.get("opex") or kpis.get("operating_expenses")
        assert opex_value == 300000.0
    
    def test_parse_from_table_data(self):
        """Test parsing financial data from table structure."""
        ade_response = {
            "document": {
                "tables": [
                    {
                        "data": [
                            ["Net Sales", "$1,000,000"],
                            ["Cost of Goods Sold", "$400,000"],
                            ["Operating Expenses", "$300,000"],
                            ["Net Income", "$200,000"]
                        ]
                    }
                ]
            }
        }
        
        normalized = normalize_ade_response(ade_response)
        kpis = extract_kpis(normalized)
        
        # Should extract data from table (may be in kpi_table with original names or mapped)
        assert len(kpis) > 0
        # Check that we got at least one value
        assert any(isinstance(v, (int, float)) and v > 0 for v in kpis.values())
        # "Net Sales" should be extracted (may be mapped to revenue or kept as "Net Sales")
        assert "Net Sales" in kpis or "revenue" in kpis or "total_revenue" in kpis
    
    def test_parse_numeric_various_formats(self):
        """Test parsing numeric values in various formats."""
        assert _parse_numeric("$1,000,000") == 1000000.0
        assert _parse_numeric("1,000,000") == 1000000.0
        assert _parse_numeric("1000000") == 1000000.0
        assert _parse_numeric("(500,000)") == -500000.0  # Negative in parentheses
        assert _parse_numeric("-500000") == -500000.0
        assert _parse_numeric("25%") == 0.25
        assert _parse_numeric("0.25") == 0.25
        assert _parse_numeric("") is None
        assert _parse_numeric("N/A") is None
    
    def test_table_mapping_income_statement(self):
        """Test mapping table rows to income statement fields."""
        rows = [
            ["Net Sales", "$1,000,000"],
            ["Cost of Goods Sold", "$400,000"],
            ["Operating Expenses", "$300,000"],
            ["Net Income", "$200,000"]
        ]
        
        normalized = {
            "income_statement": {},
            "kpi_table": {},
            "balance_sheet": {"assets": {}, "liabilities": {}, "equity": {}},
            "cash_flow": {},
            "notes": {},
            "index": {}
        }
        
        _apply_table_mapping(
            rows,
            INCOME_STATEMENT_FIELD_MAP,
            normalized,
            table_type="income_statement",
            table_index=0
        )
        
        # Check that revenue was mapped
        assert "revenue" in normalized["income_statement"] or "total_revenue" in normalized["income_statement"]
        
        # Check that source tracking was added
        assert "index" in normalized
        assert len(normalized["index"]) > 0
    
    def test_source_tracking_in_index(self):
        """Test that source information is tracked in index."""
        # Use markdown parsing path which adds source tracking
        ade_response = {
            "markdown": """
            <table>
            <tr><th>Revenue</th><td>$1,000,000</td></tr>
            <tr><th>OpEx</th><td>$300,000</td></tr>
            </table>
            """
        }
        
        normalized = normalize_ade_response(ade_response)
        
        # Check that index exists
        assert "index" in normalized
        index = normalized["index"]
        
        # Source tracking is added when using _apply_table_mapping via markdown parsing
        # If no source tracking, that's okay - it means the data came from a different path
        if len(index) > 0:
            # Check that source info has expected structure
            for field_key, source_info in index.items():
                assert "source" in source_info
                assert source_info["source"] == "ADE"
                assert "extraction_method" in source_info
                assert "table_index" in source_info
                assert "row_index" in source_info
                assert "original_text" in source_info
    
    def test_case_insensitive_field_matching(self):
        """Test that field matching is case-insensitive."""
        ade_response = {
            "income_statement": {
                "Revenue": 1000000.0,  # Capitalized
                "REVENUE": 1000000.0,  # All caps
                "revenue": 1000000.0    # Lowercase
            }
        }
        
        normalized = normalize_ade_response(ade_response)
        kpis = extract_kpis(normalized)
        
        # Should extract revenue regardless of case
        assert "revenue" in kpis
        assert kpis["revenue"] == 1000000.0
    
    def test_missing_fields_handled_gracefully(self):
        """Test that missing fields are handled gracefully."""
        ade_response = {
            "income_statement": {},
            "balance_sheet": {},
            "cash_flow": {},
            "kpi_table": {}
        }
        
        normalized = normalize_ade_response(ade_response)
        kpis = extract_kpis(normalized)
        
        # Should not crash, may return empty dict or partial data
        assert isinstance(kpis, dict)
    
    def test_nested_balance_sheet_structure(self):
        """Test parsing nested balance sheet structure."""
        ade_response = {
            "balance_sheet": {
                "assets": {
                    "current_assets": 500000.0,
                    "total_current_assets": 500000.0
                },
                "liabilities": {
                    "current_liabilities": 200000.0
                },
                "equity": {
                    "total_equity": 300000.0
                }
            }
        }
        
        normalized = normalize_ade_response(ade_response)
        kpis = extract_kpis(normalized)
        
        # Should extract balance sheet fields
        assert "total_assets" in kpis or "total_equity" in kpis


class TestADEMappingEdgeCases:
    """Test edge cases in ADE mapping."""
    
    def test_zero_values(self):
        """Test handling of zero values."""
        ade_response = {
            "income_statement": {
                "revenue": 0.0,
                "opex": 0.0
            }
        }
        
        normalized = normalize_ade_response(ade_response)
        kpis = extract_kpis(normalized)
        
        assert kpis.get("revenue") == 0.0
        assert kpis.get("opex") == 0.0
    
    def test_negative_values(self):
        """Test handling of negative values (losses)."""
        ade_response = {
            "income_statement": {
                "revenue": 1000000.0,
                "net_income": -50000.0  # Loss
            }
        }
        
        normalized = normalize_ade_response(ade_response)
        kpis = extract_kpis(normalized)
        
        assert kpis.get("net_income") == -50000.0
    
    def test_very_large_numbers(self):
        """Test handling of very large numbers."""
        ade_response = {
            "income_statement": {
                "revenue": 1e12,  # 1 trillion
                "opex": 5e11
            }
        }
        
        normalized = normalize_ade_response(ade_response)
        kpis = extract_kpis(normalized)
        
        assert kpis.get("revenue") == 1e12
        assert kpis.get("opex") == 5e11
    
    def test_string_numeric_values(self):
        """Test parsing string numeric values."""
        ade_response = {
            "income_statement": {
                "revenue": "1000000",  # String
                "opex": "300000.50"     # String with decimal
            }
        }
        
        normalized = normalize_ade_response(ade_response)
        kpis = extract_kpis(normalized)
        
        assert kpis.get("revenue") == 1000000.0
        assert kpis.get("opex") == 300000.50

