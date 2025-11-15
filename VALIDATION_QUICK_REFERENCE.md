# Validation and Testing Quick Reference

## 🎯 Where to Find Everything

### Test Cases

| Test Type | File | Count | Status |
|-----------|------|-------|--------|
| **Unit Tests** | `tests/test_financial_formulas.py` | 11 | ✅ |
| **Unit Tests** | `tests/test_balance_sheet_checker.py` | 8 | ✅ |
| **Edge Cases** | `tests/test_edge_cases.py` | 29 | ✅ NEW |
| **Integration** | `tests/test_integration.py` | 14 | ✅ NEW |
| **Total** | | **62 passing** | ✅ |

### Validation Functions

| Function | Location | What It Validates |
|----------|----------|-------------------|
| `validate_simulation_output()` | `src/validators.py` | Simulation structure, NaN/Inf, percentiles |
| `validate_monte_carlo_results()` | `src/validators.py` | Monte Carlo percentile ordering |
| `validate_critic_output()` | `src/validators.py` | Critic verdict, fixes, constraints |
| `validate_evaluation_output()` | `src/validators.py` | Evaluation status, final simulation |
| `validate_user_controls()` | `src/validators.py` | User input ranges, extreme values |

### Runtime Validation

| Engine | Location | When Validated |
|--------|----------|----------------|
| **Simulation Engine** | `src/simulation.py` | After simulation completes |
| **Critic Engine** | `src/critic.py` | After critique completes |
| **Evaluator Engine** | `src/evaluator.py` | After evaluation completes |
| **User Controls** | `src/simulation.py` | Before simulation starts |

### Constraint Checks

| Check | Location | Function |
|-------|----------|----------|
| **Balance Sheet** | `src/balance_sheet_checker.py` | `check_balance_sheet_balance()` |
| **Cash Flow** | `src/balance_sheet_checker.py` | `check_cash_flow_consistency()` |
| **Financial Ratios** | `src/balance_sheet_checker.py` | `validate_financial_ratios()` |
| **Historical Ranges** | `src/balance_sheet_checker.py` | `check_historical_ranges()` |

## 🧪 Running Tests

```bash
# All tests
pytest tests/ -v

# Edge cases only
pytest tests/test_edge_cases.py -v

# Integration tests only
pytest tests/test_integration.py -v

# Specific test
pytest tests/test_edge_cases.py::TestFinancialFormulasEdgeCases::test_negative_revenue -v
```

## 📋 What Gets Validated

### ✅ Simulation Outputs
- Required fields (formula_projections, monte_carlo, assumption_log)
- Data types (numeric vs None/string)
- NaN/Inf detection
- Percentile ordering (p10 ≤ median ≤ p90)
- Formula completeness

### ✅ Critic Outputs
- Verdict ("approve" or "revise")
- Constraint checks completeness
- Suggested fixes when verdict is "revise"

### ✅ Evaluation Outputs
- Status ("approved" or "revised")
- Final simulation validity
- Applied fixes documentation

### ✅ User Controls
- Delta ranges (warns if >1000 bps)
- Discount rate bounds (0% to 100%)
- Negative rate detection

## 📊 Test Coverage

**Total**: 63 tests
- ✅ 62 passing
- ⚠️ 1 skipped (requires API keys)
- ❌ 0 failing

**Coverage Areas**:
- ✅ Financial formulas (basic + edge cases)
- ✅ Balance sheet validation (basic + edge cases)
- ✅ Simulation outputs
- ✅ Critic outputs
- ✅ Evaluation outputs
- ✅ User controls
- ✅ Integration scenarios

