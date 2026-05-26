# JobApply AI

A smart job-application agent. You upload your CVs, it finds relevant jobs, identifies gaps
between your profile and those jobs, runs a targeted interview to fill the gaps, then
generates tailored applications.

## Getting Started

### 1. Prerequisites

- **Python 3.9 or newer.** Check with `python3 --version`. If you don't have it,
  install from [python.org](https://www.python.org/downloads/) or via Homebrew:
  `brew install python` on macOS.
- **An LLM**, one of:
  - **Google Gemini API key** (free, easiest). Grab one at
    [aistudio.google.com/apikey](https://aistudio.google.com/apikey).
  - **Ollama** running locally — no API key, no quotas. See
    [Run the LLM locally](#optional-run-the-llm-locally-no-quotas) below.
- **A SerpAPI key** (free tier available) for job search:
  [serpapi.com](https://serpapi.com).

### 2. Set up a virtual environment

A virtual environment (`venv`) is an isolated Python install for this project so its
dependencies don't pollute your system. From the repo root:

```bash
# Create the environment
python3 -m venv .venv

# Activate it:
source .venv/bin/activate      # macOS/Linux
.venv\Scripts\activate         # Windows
```

You'll need to re-run the `source` line every time you open a new terminal.

### 3. Install dependencies

```bash
make install
# or, equivalently:
pip install -r requirements.txt
```

### 4. Configure API keys

**Using Gemini (default):** on first launch the web UI asks for your Google API key and
stores it in your OS keychain. You won't be asked again.

**Using Ollama instead:** create a `.env` file with `LLM_MODEL=ollama/auto` — the app
will skip the Gemini key prompt entirely.

For SerpAPI (job search) or a file-based setup, add the keys you need to `.env`:

```bash
# .env
GOOGLE_API_KEY=your-gemini-key   # omit if using Ollama
SERPAPI_KEY=your-serpapi-key
LLM_MODEL=ollama/auto            # omit to use Gemini
```

### 5. Run it

```bash
streamlit run app.py
```

This opens the web UI in your browser (usually at <http://localhost:8501>).

## Useful commands

```bash
make test               # fast unit tests (no network, no LLM calls)
make test-integration   # integration tests using cached LLM responses
make test-e2e           # full end-to-end pipeline (slow)
```

## Optional: run the LLM locally (no quotas)

For unlimited local inference, install [Ollama](https://ollama.com), then:

```bash
llama serve &           # start the local server
ollama pull qwen2.5     # downloads the default (7b)
```

Set `LLM_MODEL=ollama/auto` in your `.env` to use it instead of Gemini.
