# Troubleshooting Guide

## Issue: Same Results for Different Financial Statements

### Root Cause

The system was showing the same results for different financial statements due to:

1. **OpenAI API Failures**: The GPT-5-nano model doesn't exist as a standard OpenAI model, so API calls were failing and falling back to local simulation.

2. **Hardcoded Fallback Values**: When KPI extraction failed or returned empty results, the local simulation was using hardcoded fallback values (e.g., `revenue = 1000000`) instead of extracting actual values from the reports.

3. **Weak KPI Extraction**: The KPI extraction function wasn't robust enough to handle different JSON structures and field name variations.

4. **Local Simulation Overwriting**: Even when OpenAI API worked, the local Monte Carlo enhancement was overwriting the API results.

### Fixes Applied

1. **Improved KPI Extraction** (`src/ingestion.py`):
   - Enhanced `extract_kpis()` to handle multiple field name variations
   - Added case-insensitive matching
   - Improved parsing of numeric strings (handles "$", "," formatting)
   - Better handling of nested structures (balance sheet assets/liabilities)
   - Extracts from multiple sources: `kpi_table`, `income_statement`, `balance_sheet`, `cash_flow`

2. **Better Error Handling** (`src/simulation.py`):
   - Added debug logging to show which KPIs are extracted
   - Improved revenue extraction with multiple fallback attempts
   - Raises clear errors when revenue cannot be found (instead of using hardcoded values)
   - Better handling of 0.0 vs None values

3. **Smarter API Integration**:
   - Added debug logging to show which API path is being used
   - Only enhances with local Monte Carlo if OpenAI response is incomplete
   - Better error messages when API calls fail
   - Tries standard OpenAI API if custom endpoint fails

4. **Enhanced Field Extraction**:
   - Tries multiple field name variations (revenue, total_revenue, Revenue, etc.)
   - Checks multiple data sources (kpi_table, income_statement, etc.)
   - Handles nested structures properly

### How to Verify the Fix

1. **Check Debug Logs**: When running the simulation, you should see debug messages like:
   ```
   [DEBUG] Extracted KPIs: ['revenue', 'opex', 'net_income', ...]
   [DEBUG] Using base_revenue: 10,000,000.00
   [DEBUG] Using base_opex: 2,500,000.00
   ```

2. **Different Reports Should Show Different Values**: 
   - Upload two different financial statements
   - Check the extracted KPIs in the debug logs
   - Verify that revenue and other metrics are different

3. **Error Messages**: If revenue cannot be found, you'll get a clear error message showing:
   - Available keys in the report
   - Extracted KPIs
   - Income statement keys

### Current Behavior

- **If OpenAI API works**: Uses AI-generated simulation with local Monte Carlo enhancement (if needed)
- **If OpenAI API fails**: Falls back to local simulation using **actual data from the report**
- **If data extraction fails**: Raises clear error with diagnostic information

### API Status

The system tries APIs in this order:
1. GPT-5-nano (custom endpoint) - Likely fails (model doesn't exist)
2. GPT-4-turbo-preview (standard OpenAI API) - Should work if you have access
3. Local simulation (fallback) - Uses actual report data

### Next Steps

1. **Verify API Keys**: Make sure your OpenAI API key has access to GPT-4 models
2. **Check Logs**: Look for `[DEBUG]` and `[WARNING]` messages in the console
3. **Test with Sample Data**: Use `sample_data/sample_report.json` to verify extraction works
4. **Compare Results**: Upload two different reports and compare the extracted KPIs

## Prompts Used

See `PROMPTS.md` for the exact prompts used for:
- OpenAI Simulation
- DeepSeek Critic
- ChatGPT Evaluator

