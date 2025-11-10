# Financial Analysis Pipeline

A complete Python project that implements a comprehensive financial analysis pipeline with AI-powered simulation, critique, and evaluation.

## Features

- **Landing AI ADE Integration**: Direct PDF upload and extraction using Landing AI ADE API
- **Landing AI ADE JSON Ingestion**: Parse and validate financial reports from Landing AI ADE (also supports pre-extracted JSON files)
- **HTML Table Parsing**: Automatically maps ADE markdown tables into structured financial fields (revenue, opex, net income, balance sheet, cash flow)
- **OpenAI Simulation**: Formula-driven projections with 10,000 Monte Carlo scenarios
- **DeepSeek Critic**: Forensic review with constraint checking and validation
- **ChatGPT Evaluator**: Deterministic application of critic fixes and final report generation
- **Streamlit App**: Interactive web interface with PDF/JSON upload, real-time debate logs, and PDF export

## Project Structure

```
.
├── src/                          # Source code
│   ├── __init__.py
│   ├── ingestion.py              # Landing AI ADE JSON ingestion
│   ├── simulation.py             # OpenAI simulation engine
│   ├── critic.py                 # DeepSeek critic engine
│   ├── evaluator.py              # ChatGPT evaluator engine
│   ├── pdf_generator.py          # PDF report generation
│   ├── financial_formulas.py     # Financial calculation utilities
│   └── balance_sheet_checker.py  # Balance sheet constraint checker
├── tests/                        # Unit tests
│   ├── __init__.py
│   ├── test_financial_formulas.py
│   └── test_balance_sheet_checker.py
├── sample_data/                  # Sample datasets
│   └── sample_report.json
├── app.py                        # Streamlit application
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variables template
└── README.md                     # This file
```

## Installation

1. **Clone the repository** (or navigate to the project directory)

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and add your API keys:
   ```
   OPENAI_API_KEY=your-openai-api-key
   DEEPSEEK_API_KEY=your-deepseek-api-key
   CHATGPT_API_KEY=your-chatgpt-api-key (optional, falls back to OpenAI)
   LANDINGAI_API_KEY=your-landingai-api-key (or VISION_AGENT_API_KEY)
   ```

## Usage

### Running the Streamlit App

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

### Using the Streamlit App

1. **Upload File**: 
   - **PDF File**: Upload a PDF file to extract data using Landing AI ADE API
   - **JSON File**: Upload a pre-extracted Landing AI ADE JSON file
2. **Extract Data** (for PDFs): Click "Extract Data from PDF" to process the PDF
3. **Adjust Scenario Controls**: Use sliders to set scenario deltas:
   - OpEx Delta (basis points)
   - Revenue Delta (basis points)
   - Base Discount Rate (%)
   - Discount Rate Delta (basis points)
4. **Run Analysis**: Click "Run Analysis" to start the pipeline
5. **View Results**: 
   - **JSON Preview**: View the extracted/uploaded report data
   - **Results**: See simulation results, critic review, and evaluation
   - **Debate Logs**: Watch real-time logs of the simulation-critic debate
   - **Export**: Download the final PDF report

### Programmatic Usage

```python
from src.ingestion import load_ade_json
from src.simulation import SimulationEngine
from src.critic import CriticEngine
from src.evaluator import EvaluatorEngine
from src.pdf_generator import PDFReportGenerator
import asyncio

# Load report
report_json = load_ade_json("sample_data/sample_report.json")

# Set user controls
user_controls = {
    "opex_delta_bps": -50,
    "revenue_delta_bps": 0,
    "discount_rate_base": 0.08,
    "discount_rate_delta_bps": -200
}

# Run pipeline
async def run_pipeline():
    # Simulation
    simulation_engine = SimulationEngine()
    simulation_json = await simulation_engine.run_simulation(report_json, user_controls)
    
    # Critic
    critic_engine = CriticEngine()
    critic_json = await critic_engine.run_critique(report_json, simulation_json)
    
    # Evaluator
    evaluator_engine = EvaluatorEngine()
    evaluation_json = await evaluator_engine.evaluate(simulation_json, critic_json, report_json)
    
    # Generate PDF
    pdf_generator = PDFReportGenerator()
    pdf_path = pdf_generator.generate_report(
        report_json, simulation_json, critic_json, evaluation_json, "output.pdf"
    )
    
    return evaluation_json

# Run
result = asyncio.run(run_pipeline())
```

## Testing

Run unit tests:

```bash
pytest tests/
```

Or run specific test files:

```bash
pytest tests/test_financial_formulas.py
pytest tests/test_balance_sheet_checker.py
```

## API Keys

The project requires API keys for:

1. **Landing AI API**: For PDF extraction (ADE API) - Set as `LANDINGAI_API_KEY` or `VISION_AGENT_API_KEY`
2. **OpenAI API**: For simulation (GPT-5-nano model)
3. **DeepSeek API**: For critique and validation
4. **ChatGPT API**: For evaluation (optional, falls back to OpenAI)

API keys should be set in environment variables or in a `.env` file.

## Sample Data

A sample report JSON is provided in `sample_data/sample_report.json`. This includes:
- Income statement data
- Balance sheet data
- Cash flow statement
- KPI table
- Industry averages
- Document index mapping

## Pipeline Flow

1. **Ingestion**: Load and validate Landing AI ADE JSON
2. **Simulation**: 
   - Formula-driven projections
   - 10,000 Monte Carlo scenarios
   - Assumption logging
   - Traceability mapping
3. **Critique**:
   - Balance sheet constraint checking
   - Cash flow consistency validation
   - Industry comparison
   - Sanity tests
   - Verdict (approve/revise)
4. **Evaluation**:
   - Apply critic fixes (if revision needed)
   - Generate final simulation
   - Create assumption log
5. **Report Generation**:
   - Generate PDF with all results
   - Include projections, Monte Carlo results, critic review, and applied fixes

## Financial Formulas

The project includes implementations of standard financial formulas:

- EBITDA calculation
- EBIT calculation
- Net Income calculation
- Free Cash Flow calculation
- NPV calculation
- IRR calculation (manual implementation)
- Monte Carlo simulation
- Percentile calculations

## Balance Sheet Checker

The balance sheet checker validates:

- Balance sheet balancing (Assets = Liabilities + Equity)
- Cash flow consistency
- Financial ratios vs industry averages
- Historical range validation

## Error Handling

The pipeline includes comprehensive error handling:

- API failures fall back to local calculations
- Invalid JSON is caught and reported
- Missing fields are handled gracefully
- Constraint violations are logged and reported

## License

This project is provided as-is for educational and research purposes.

## Contributing

Contributions are welcome! Please ensure:

- Code follows PEP 8 style guidelines
- Tests are added for new features
- Documentation is updated
- All tests pass before submitting

## Support

For issues or questions, please open an issue on the repository.
