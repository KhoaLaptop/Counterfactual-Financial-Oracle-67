# Financial Model Documentation

## Model Type: Discounted Cash Flow (DCF)

This system uses a **Discounted Cash Flow (DCF) model** for valuation and financial projections.

## Model Structure

### 1. Income Statement Projections

The model projects financial metrics using the following formula chain:

```
Revenue (adjusted) = Base Revenue × (1 + revenue_delta_bps / 10,000)

OpEx (adjusted) = Base OpEx × (1 + opex_delta_bps / 10,000)

EBITDA = Revenue - COGS - OpEx
  Formula: EBITDA = Revenue - Cost of Goods Sold - Operating Expenses

EBIT = EBITDA - Depreciation - Amortization
  Formula: EBIT = EBITDA - D&A

Net Income = (EBIT - Interest Expense + Other Income) × (1 - Tax Rate)
  Formula: Net Income = (EBIT - Interest + Other Income) × (1 - Tax Rate)
```

### 2. Cash Flow Projections

```
Free Cash Flow (FCF) = Net Income + Depreciation + Amortization - CapEx - ΔWorking Capital
  Formula: FCF = Net Income + D&A - Capital Expenditures - Change in Working Capital
```

### 3. Valuation (DCF)

The system uses a **5-year DCF model** with constant cash flow assumption:

```
NPV = Σ [FCF / (1 + r)^t] for t = 1 to 5

Where:
  - FCF = Free Cash Flow (assumed constant for 5 years)
  - r = Discount Rate = discount_rate_base + (discount_rate_delta_bps / 10,000)
  - t = Year (1, 2, 3, 4, 5)
```

**Note**: This is a simplified DCF model. A full DCF would include:
- Terminal value calculation
- Multi-year cash flow projections with growth rates
- WACC (Weighted Average Cost of Capital) calculation
- Enterprise Value adjustments

### 4. Monte Carlo Simulation

The system runs **10,000 Monte Carlo scenarios** using:
- **Distribution**: Normal distribution (default)
- **Parameters**: 
  - Mean delta from user controls
  - Standard deviation: 1-2% (configurable)
- **Outputs**: Median, 10th percentile, 90th percentile for all key metrics

## Formula Reference

### EBITDA Calculation
```
EBITDA = Revenue - COGS - OpEx
```

### EBIT Calculation
```
EBIT = EBITDA - Depreciation - Amortization
```

### Net Income Calculation
```
EBT = EBIT - Interest Expense + Other Income
Net Income = EBT × (1 - Tax Rate)
```

### Free Cash Flow Calculation
```
FCF = Net Income + Depreciation + Amortization - CapEx - ΔWorking Capital + Other Adjustments
```

### NPV Calculation
```
NPV = -Initial Investment + Σ [CF_t / (1 + r)^t] for t = 1 to n

Where:
  CF_t = Cash flow in period t
  r = Discount rate
  n = Number of periods (5 years in this model)
```

### IRR Calculation
```
IRR is the discount rate where NPV = 0

Solved using Newton-Raphson method:
  NPV(IRR) = Σ [CF_t / (1 + IRR)^t] = 0
```

## Model Assumptions

1. **Constant Cash Flows**: FCF is assumed constant for 5 years (simplified model)
2. **No Terminal Value**: Model does not include terminal value calculation
3. **No Growth Rates**: No explicit growth rate assumptions in base model
4. **Single Discount Rate**: Uses a single discount rate for all periods
5. **Normal Distribution**: Monte Carlo uses normal distribution by default

## Model Limitations

1. **Simplified DCF**: Does not include terminal value or multi-year growth projections
2. **Constant Cash Flows**: Assumes constant FCF over projection period
3. **No WACC Calculation**: Uses user-provided discount rate directly
4. **No Sensitivity Analysis**: Limited to Monte Carlo simulation only

## Future Enhancements

1. Add terminal value calculation (Gordon Growth Model or Exit Multiple)
2. Add multi-year cash flow projections with growth rates
3. Add WACC calculation from balance sheet data
4. Add sensitivity analysis (tornado diagrams)
5. Add scenario analysis (base, optimistic, pessimistic)

