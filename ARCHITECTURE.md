# Architecture Documentation

## System Overview

The Counterfactual Financial Oracle is a comprehensive financial analysis pipeline that processes financial reports through multiple AI-powered stages to generate validated financial projections and reports.

## High-Level Architecture

```mermaid
graph TB
    subgraph "User Interface Layer"
        UI[Streamlit Web Application<br/>app.py]
        CLI[Command Line Interface<br/>main.py]
    end
    
    subgraph "Data Ingestion Layer"
        PDF_Input[PDF Financial Reports]
        JSON_Input[Pre-extracted JSON Files]
        ADE_API[Landing AI ADE API<br/>Document Extraction]
        Ingestion[Ingestion Module<br/>src/ingestion.py]
    end
    
    subgraph "Core Processing Pipeline"
        Sim[Simulation Engine<br/>src/simulation.py<br/>OpenAI GPT-5-nano]
        Critic[Critic Engine<br/>src/critic.py<br/>DeepSeek API]
        Eval[Evaluator Engine<br/>src/evaluator.py<br/>ChatGPT/OpenAI]
    end
    
    subgraph "Supporting Services"
        Formulas[Financial Formulas<br/>src/financial_formulas.py]
        BS_Check[Balance Sheet Checker<br/>src/balance_sheet_checker.py]
    end
    
    subgraph "Output Generation"
        PDF_Gen[PDF Generator<br/>src/pdf_generator.py]
        Reports[Final Reports]
    end
    
    UI --> Ingestion
    CLI --> Ingestion
    PDF_Input --> ADE_API
    JSON_Input --> Ingestion
    ADE_API --> Ingestion
    
    Ingestion --> Sim
    Sim --> Formulas
    Formulas --> Sim
    
    Sim --> Critic
    Critic --> BS_Check
    BS_Check --> Critic
    
    Critic --> Eval
    Eval --> Formulas
    
    Eval --> PDF_Gen
    Eval --> UI
    PDF_Gen --> Reports
    
    style Sim fill:#e1f5ff,stroke:#0066cc,stroke-width:2px
    style Critic fill:#fff4e1,stroke:#cc6600,stroke-width:2px
    style Eval fill:#e1ffe1,stroke:#00cc00,stroke-width:2px
    style ADE_API fill:#ffe1f5,stroke:#cc0066,stroke-width:2px
    style PDF_Gen fill:#f0e1ff,stroke:#6600cc,stroke-width:2px
```

## Detailed Component Architecture

### 1. Data Ingestion Layer

```mermaid
graph LR
    subgraph "Input Sources"
        PDF[PDF Files]
        JSON[JSON Files]
    end
    
    subgraph "Ingestion Module (src/ingestion.py)"
        ADE[Landing AI ADE<br/>API Client]
        Parser[JSON Parser]
        Validator[Data Validator]
        Normalizer[Data Normalizer]
        TableExt[Table Extractor<br/>HTML/Markdown]
        FieldMap[Field Mapper]
    end
    
    subgraph "Output"
        Normalized[Normalized JSON<br/>- income_statement<br/>- balance_sheet<br/>- cash_flow<br/>- kpi_table<br/>- index]
    end
    
    PDF --> ADE
    JSON --> Parser
    ADE --> TableExt
    TableExt --> FieldMap
    Parser --> Validator
    FieldMap --> Normalizer
    Validator --> Normalizer
    Normalizer --> Normalized
    
    style ADE fill:#ffe1f5
    style Normalizer fill:#e1f5ff
```

**Key Functions:**
- `extract_from_pdf()`: Extracts data from PDF using Landing AI ADE API
- `extract_from_pdf_bytes()`: Handles PDF bytes directly
- `load_ade_json()`: Loads pre-extracted JSON files
- `normalize_ade_response()`: Normalizes ADE response to standard format
- `validate_report_json()`: Validates report structure
- `extract_kpis()`: Extracts key performance indicators
- `_populate_financials_from_markdown()`: Parses HTML tables from markdown

### 2. Simulation Engine

```mermaid
graph TB
    subgraph "Input"
        Report[Report JSON]
        Controls[User Controls<br/>- OpEx Delta<br/>- Revenue Delta<br/>- Discount Rate]
    end
    
    subgraph "Simulation Engine (src/simulation.py)"
        OpenAI_API[OpenAI API<br/>GPT-5-nano]
        FormulaCalc[Formula Calculations]
        MonteCarlo[Monte Carlo Simulation<br/>10,000 scenarios]
        AssumptionLog[Assumption Logger]
        Traceability[Traceability Mapper]
    end
    
    subgraph "Supporting"
        Formulas[Financial Formulas Module]
    end
    
    subgraph "Output"
        SimResults[Simulation JSON<br/>- formula_projections<br/>- monte_carlo<br/>- assumption_log<br/>- traceability]
    end
    
    Report --> OpenAI_API
    Controls --> OpenAI_API
    OpenAI_API --> FormulaCalc
    FormulaCalc --> Formulas
    Formulas --> MonteCarlo
    MonteCarlo --> AssumptionLog
    AssumptionLog --> Traceability
    Traceability --> SimResults
    
    style OpenAI_API fill:#e1f5ff
    style MonteCarlo fill:#fff4e1
```

**Key Functions:**
- `run_simulation()`: Main simulation orchestration
- Uses OpenAI API for intelligent formula-driven projections
- Runs 10,000 Monte Carlo scenarios locally
- Generates assumption logs and traceability mappings
- Falls back to local calculations if API fails

**Financial Formulas Used:**
- EBITDA = Revenue - COGS - OpEx
- EBIT = EBITDA - Depreciation - Amortization
- Net Income = (EBIT - Interest + Other Income) × (1 - Tax Rate)
- Free Cash Flow = Cash from Operations - CapEx
- NPV calculation with discount rate
- IRR calculation

### 3. Critic Engine

```mermaid
graph TB
    subgraph "Input"
        Report[Report JSON]
        SimResults[Simulation Results]
    end
    
    subgraph "Critic Engine (src/critic.py)"
        DeepSeek_API[DeepSeek API]
        ConstraintCheck[Constraint Checks]
        IndustryComp[Industry Comparison]
        SanityTests[Sanity Tests]
        Explainability[Explainability Check]
    end
    
    subgraph "Balance Sheet Checker"
        BS_Balance[Balance Sheet Balance Check]
        CF_Consistency[Cash Flow Consistency]
        RatioCheck[Financial Ratio Validation]
        HistoricalCheck[Historical Range Check]
    end
    
    subgraph "Output"
        CriticResults[Critic JSON<br/>- verdict<br/>- constraint_checks<br/>- suggested_fixes]
    end
    
    Report --> DeepSeek_API
    SimResults --> DeepSeek_API
    DeepSeek_API --> ConstraintCheck
    ConstraintCheck --> BS_Balance
    ConstraintCheck --> CF_Consistency
    ConstraintCheck --> RatioCheck
    ConstraintCheck --> HistoricalCheck
    BS_Balance --> IndustryComp
    CF_Consistency --> IndustryComp
    IndustryComp --> SanityTests
    SanityTests --> Explainability
    Explainability --> CriticResults
    
    style DeepSeek_API fill:#fff4e1
    style BS_Balance fill:#ffe1f5
```

**Key Functions:**
- `run_critique()`: Main critique orchestration
- Uses DeepSeek API for intelligent validation
- Performs constraint checks via `balance_sheet_checker.py`
- Compares against industry averages
- Validates historical ranges
- Provides verdict (approve/revise) and suggested fixes

**Validation Checks:**
- Balance sheet balancing (Assets = Liabilities + Equity)
- Cash flow consistency
- Financial ratios vs industry averages
- Historical range validation
- Growth rate sanity checks
- Margin validation

### 4. Evaluator Engine

```mermaid
graph TB
    subgraph "Input"
        SimResults[Simulation Results]
        CriticResults[Critic Results]
        Report[Report JSON]
    end
    
    subgraph "Evaluator Engine (src/evaluator.py)"
        ChatGPT_API[ChatGPT/OpenAI API]
        FixApplier[Fix Application Logic]
        RevisionEngine[Revision Engine]
        FinalCalc[Final Calculations]
    end
    
    subgraph "Supporting"
        Formulas[Financial Formulas]
    end
    
    subgraph "Output"
        EvalResults[Evaluation JSON<br/>- final_simulation<br/>- applied_fixes<br/>- assumption_log<br/>- status]
    end
    
    SimResults --> ChatGPT_API
    CriticResults --> ChatGPT_API
    Report --> ChatGPT_API
    ChatGPT_API --> FixApplier
    FixApplier --> RevisionEngine
    RevisionEngine --> Formulas
    Formulas --> FinalCalc
    FinalCalc --> EvalResults
    
    style ChatGPT_API fill:#e1ffe1
    style FixApplier fill:#fff4e1
```

**Key Functions:**
- `evaluate()`: Main evaluation orchestration
- Uses ChatGPT/OpenAI API for intelligent fix application
- Applies critic fixes deterministically
- Recalculates formulas and Monte Carlo if needed
- Generates final assumption log
- Falls back to local fix application if API fails

### 5. PDF Generator

```mermaid
graph TB
    subgraph "Input"
        Report[Report JSON]
        SimResults[Simulation Results]
        CriticResults[Critic Results]
        EvalResults[Evaluation Results]
    end
    
    subgraph "PDF Generator (src/pdf_generator.py)"
        ReportLab[ReportLab Library]
        DocBuilder[Document Builder]
        TableGen[Table Generator]
        StyleEngine[Style Engine]
    end
    
    subgraph "Output"
        PDF[PDF Report<br/>- Executive Summary<br/>- Formula Projections<br/>- Monte Carlo Results<br/>- Critic Review<br/>- Applied Fixes]
    end
    
    Report --> DocBuilder
    SimResults --> DocBuilder
    CriticResults --> DocBuilder
    EvalResults --> DocBuilder
    DocBuilder --> ReportLab
    ReportLab --> TableGen
    ReportLab --> StyleEngine
    TableGen --> PDF
    StyleEngine --> PDF
    
    style ReportLab fill:#f0e1ff
```

**Key Functions:**
- `generate_report()`: Generates PDF file
- `generate_report_bytes()`: Generates PDF as bytes (for Streamlit)
- `_build_story()`: Builds document structure
- Includes all analysis results, charts, and tables

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant UI as Streamlit UI
    participant Ingestion
    participant Sim as Simulation Engine
    participant Critic
    participant Eval as Evaluator Engine
    participant PDF as PDF Generator
    
    User->>UI: Upload PDF/JSON
    UI->>Ingestion: Extract/Validate Data
    Ingestion-->>UI: Normalized JSON
    
    User->>UI: Set Controls & Run Analysis
    UI->>Sim: Run Simulation
    Sim->>Sim: Formula Calculations
    Sim->>Sim: Monte Carlo (10k scenarios)
    Sim-->>UI: Simulation Results
    
    UI->>Critic: Run Critique
    Critic->>Critic: Constraint Checks
    Critic->>Critic: Industry Comparison
    Critic->>Critic: Sanity Tests
    Critic-->>UI: Critique Results (verdict)
    
    alt Verdict == "revise"
        UI->>Eval: Apply Fixes
        Eval->>Eval: Recalculate Formulas
        Eval->>Eval: Re-run Monte Carlo
        Eval-->>UI: Revised Results
    else Verdict == "approve"
        Eval-->>UI: Approved Results
    end
    
    UI->>PDF: Generate Report
    PDF-->>User: Download PDF
```

## Module Dependencies

```mermaid
graph TD
    app.py --> ingestion
    app.py --> simulation
    app.py --> critic
    app.py --> evaluator
    app.py --> pdf_generator
    
    main.py --> ingestion
    main.py --> simulation
    main.py --> critic
    main.py --> evaluator
    main.py --> pdf_generator
    
    simulation --> financial_formulas
    simulation --> ingestion
    
    critic --> balance_sheet_checker
    
    evaluator --> financial_formulas
    
    pdf_generator --> reportlab
    
    style app.py fill:#e1f5ff
    style main.py fill:#e1f5ff
    style simulation fill:#fff4e1
    style critic fill:#ffe1f5
    style evaluator fill:#e1ffe1
```

## External API Integration

```mermaid
graph LR
    subgraph "Application"
        App[Counterfactual Financial Oracle]
    end
    
    subgraph "External APIs"
        LandingAI[Landing AI ADE API<br/>Document Extraction]
        OpenAI[OpenAI API<br/>GPT-5-nano / GPT-4]
        DeepSeek[DeepSeek API<br/>deepseek-chat]
        ChatGPT[ChatGPT API<br/>GPT-4-turbo]
    end
    
    App -->|PDF Upload| LandingAI
    App -->|Simulation| OpenAI
    App -->|Critique| DeepSeek
    App -->|Evaluation| ChatGPT
    
    style LandingAI fill:#ffe1f5
    style OpenAI fill:#e1f5ff
    style DeepSeek fill:#fff4e1
    style ChatGPT fill:#e1ffe1
```

## Error Handling & Fallbacks

```mermaid
graph TB
    subgraph "Primary Path"
        API_Call[API Call]
    end
    
    subgraph "Fallback Strategy"
        Check{API Success?}
        Fallback[Local Calculation]
        Error[Error Logging]
    end
    
    API_Call --> Check
    Check -->|Success| Continue[Continue Pipeline]
    Check -->|Failure| Fallback
    Fallback --> Continue
    Check -->|Critical Error| Error
    
    style API_Call fill:#e1f5ff
    style Fallback fill:#fff4e1
    style Error fill:#ffe1f5
```

**Fallback Mechanisms:**
1. **Landing AI ADE**: Falls back to HTTP API if SDK fails
2. **OpenAI Simulation**: Falls back to local formula calculations
3. **DeepSeek Critic**: Falls back to local constraint checks
4. **ChatGPT Evaluator**: Falls back to local fix application

## Testing Architecture

```mermaid
graph TB
    subgraph "Test Suite"
        TestFormulas[test_financial_formulas.py]
        TestBS[test_balance_sheet_checker.py]
    end
    
    subgraph "Modules Under Test"
        Formulas[financial_formulas.py]
        BS_Checker[balance_sheet_checker.py]
    end
    
    TestFormulas --> Formulas
    TestBS --> BS_Checker
    
    style TestFormulas fill:#e1ffe1
    style TestBS fill:#e1ffe1
```

## Security Architecture

```mermaid
graph TB
    subgraph "Environment"
        EnvFile[.env file<br/>Not in Git]
        EnvVars[Environment Variables]
    end
    
    subgraph "API Keys"
        OpenAI_Key[OPENAI_API_KEY]
        DeepSeek_Key[DEEPSEEK_API_KEY]
        ChatGPT_Key[CHATGPT_API_KEY]
        LandingAI_Key[LANDINGAI_API_KEY]
    end
    
    EnvFile --> EnvVars
    EnvVars --> OpenAI_Key
    EnvVars --> DeepSeek_Key
    EnvVars --> ChatGPT_Key
    EnvVars --> LandingAI_Key
    
    style EnvFile fill:#ffe1f5
    style EnvVars fill:#e1f5ff
```

## Performance Considerations

1. **Async Operations**: All API calls use async/await for parallel processing
2. **Local Monte Carlo**: 10,000 scenarios run locally (fast NumPy operations)
3. **Caching**: Session state in Streamlit for intermediate results
4. **Efficient PDF Generation**: ReportLab for fast PDF creation

## Scalability

- **Stateless Design**: Each pipeline run is independent
- **Modular Architecture**: Easy to add new engines or validators
- **API-Based**: Can be containerized and deployed as microservices
- **Streamlit UI**: Can be deployed to Streamlit Cloud or self-hosted

## Future Enhancements

1. **Database Integration**: Store results in database for historical analysis
2. **Batch Processing**: Process multiple reports simultaneously
3. **Advanced Visualizations**: Charts and graphs in PDF and UI
4. **Export Formats**: Excel, CSV, JSON exports
5. **User Authentication**: Secure access to the Streamlit app
6. **Historical Analysis**: Track changes over time
7. **Custom Reports**: User-defined report templates

