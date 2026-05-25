# JobApply AI — Claude Code Instructions

## What This Project Is
A smart job application agent for multiple candidates. Each candidate uploads their CVs,
the system finds relevant jobs, identifies gaps between their profile and those jobs,
runs a targeted interview to fill only the relevant gaps, then generates tailored applications.

## Start of Every Session
1. Ask which candidate you're working with (or list existing ones in `candidates/`)
2. Read `candidates/[id]/tracker.json` — understand current stage and what's done
3. Read `candidates/[id]/profile.json` — know what we already know
4. Check `candidates/[id]/gap_report.json` if it exists — know what gaps remain
5. Read `PLAN.md` — check overall build status
6. Never repeat work already done

## The Funnel (in order)
1. Upload CVs → parse → profile.json
2. Screen jobs → shortlist
3. Gap analysis → gap_report.json
4. Targeted interview → enrich profile.json
5. Generate tailored applications

## Key Rules
- Each candidate is fully isolated under `candidates/[candidate_id]/`
- `tracker.json` (per candidate) is the source of truth — always update after any action
- Interview questions must be driven by `gap_report.json` — not generic
- One question at a time during interviews
- API keys stored in `.env` (never commit)

## LLM Provider — Free Tier First
**Production: Google Gemini. Testing: Ollama (local, unlimited).**
- All scripts use `LLMClient` from `scripts/llm_client.py` — never call any provider directly
- Production default: `gemini/gemini-2.0-flash` (15 RPM, 1,500 RPD)
- Testing default: `ollama/llama3.2` — local, unlimited, no API key needed
- Rate-limit fallback: if Gemini hits 15 RPM, LLMClient automatically routes to Ollama (no wait)
- Do NOT add `anthropic` or `groq` calls — the goal is a fully free pipeline
- If a new script needs an LLM call, always use `LLMClient().chat(prompt, max_tokens=N)`
- Override model via `LLM_MODEL` env var; override test model via `TEST_LLM_MODEL`

## Environment Variables (.env)
```
GOOGLE_API_KEY=        # Required for production — https://aistudio.google.com/apikey
SERPAPI_KEY=           # Required for job search (screen_jobs.py)
LLM_MODEL=             # Optional — override production model (e.g. ollama/llama3.2 for local)
LLM_FALLBACK_MODEL=    # Optional — Ollama model for rate-limit fallback (default: ollama/llama3.2)
OLLAMA_BASE_URL=       # Optional — default http://localhost:11434
TEST_LLM_MODEL=        # Optional — override model used when rebuilding test cache
```

## Current Next Step
All tests green: 53 unit + 31 integration. Ollama provider fully working. Privacy audit done.

**START HERE:**
1. `make test-e2e` — run full pipeline for Alex Müller (Stages 1–6). Has never been run end-to-end.
2. `streamlit run app.py` — manual UI walkthrough using the checklist in PLAN.md
3. Phase 2 improvements — see IDEAS.md and PLAN.md Phase 2 section

**Ollama setup (if server not running):**
- `ollama serve &` — start in background
- `ollama pull qwen2.5:7b` — best model for M5 16GB
- Set `LLM_MODEL=ollama/auto` in `.env` for local testing
