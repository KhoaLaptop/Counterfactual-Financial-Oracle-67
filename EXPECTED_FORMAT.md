# Expected JSON Format

The financial analysis pipeline expects JSON files in the following format:

## Required Structure

```json
{
  "income_statement": {
    "revenue": 10000000,
    "total_revenue": 10000000,
    "operating_expenses": 2500000,
    "opex": 2500000,
    "cost_of_goods_sold": 3000000,
    "cogs": 3000000,
    "depreciation": 500000,
    "amortization": 100000,
    "ebitda": 4500000,
    "ebit": 3900000,
    "interest_expense": 200000,
    "tax_rate": 0.25,
    "net_income": 2775000
  },
  "balance_sheet": {
    "assets": {
      "cash": 2000000,
      "accounts_receivable": 1500000,
      "inventory": 1000000,
      "property_plant_equipment": 8000000,
      "total_assets": 12500000
    },
    "liabilities": {
      "accounts_payable": 1000000,
      "short_term_debt": 500000,
      "long_term_debt": 5000000,
      "total_liabilities": 6500000
    },
    "equity": {
      "common_stock": 2000000,
      "retained_earnings": 4000000,
      "total_equity": 6000000
    }
  },
  "cash_flow": {
    "cash_from_operations": 3875000,
    "operating_cash_flow": 3875000,
    "depreciation": 500000,
    "amortization": 100000,
    "working_capital_changes": 0,
    "capital_expenditures": 1000000,
    "capex": 1000000,
    "free_cash_flow": 2875000
  },
  "kpi_table": {
    "revenue": 10000000,
    "ebitda": 4500000,
    "ebitda_margin": 45.0,
    "net_income": 2775000,
    "net_margin": 27.75
  },
  "notes": {},
  "index": {}
}
```

## Minimum Required Fields

At minimum, the JSON must have:
- `income_statement.revenue` OR `income_statement.total_revenue` OR `kpi_table.revenue`

## Common Issues

1. **Empty dictionaries**: If you have `"income_statement": {}`, the system cannot extract data
2. **Missing revenue**: Revenue is required for the simulation to work
3. **Wrong data types**: Values should be numbers, not strings (e.g., `10000000` not `"10,000,000"`)

## Example Valid File

See `sample_data/sample_report.json` for a complete example.

