# Environment Setup Guide

## Prerequisites

- Python 3.8 or higher
- pip package manager

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Set Up Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your API keys:
   ```
   LANDINGAI_API_KEY=YOUR_LANDINGAI_API_KEY
   OPENAI_API_KEY=YOUR_OPENAI_API_KEY
   DEEPSEEK_API_KEY=YOUR_DEEPSEEK_API_KEY
   CHATGPT_API_KEY=your-chatgpt-api-key-here
   ```

   Notes:
   - `LANDINGAI_API_KEY`: Used for PDF extraction via Landing AI ADE API (can also be set as `VISION_AGENT_API_KEY`)
   - `CHATGPT_API_KEY`: Optional, falls back to `OPENAI_API_KEY` if not provided

## Step 3: Verify Installation

Run the tests to verify everything is set up correctly:

```bash
pytest tests/
```

## Step 4: Run the Application

Start the Streamlit app:

```bash
streamlit run app.py
```

The app will be available at `http://localhost:8501`.

## Troubleshooting

### API Key Issues

If you encounter API key errors:

1. Verify your API keys are correct in the `.env` file
2. Ensure the `.env` file is in the project root directory
3. Check that `python-dotenv` is installed: `pip install python-dotenv`
4. For Landing AI API: Make sure `LANDINGAI_API_KEY` or `VISION_AGENT_API_KEY` is set
5. For PDF extraction: Ensure the `landingai-ade` library is installed: `pip install landingai-ade`

### Import Errors

If you encounter import errors:

1. Ensure you're in the project root directory
2. Verify all dependencies are installed: `pip install -r requirements.txt`
3. Check that Python can find the `src` module (it should be in the same directory)

### API Connection Issues

If API calls fail:

1. Check your internet connection
2. Verify API keys are valid and have sufficient credits
3. Check API service status
4. The pipeline will fall back to local calculations if APIs are unavailable

### PDF Generation Issues

If PDF generation fails:

1. Ensure `reportlab` is installed: `pip install reportlab`
2. Check that you have write permissions in the output directory
3. Verify the report data is valid JSON

## Development Setup

For development, you may want to install additional tools:

```bash
pip install black flake8 mypy
```

Run code formatting:

```bash
black src/ tests/ app.py
```

Run linting:

```bash
flake8 src/ tests/ app.py
```

Run type checking:

```bash
mypy src/ app.py
```

