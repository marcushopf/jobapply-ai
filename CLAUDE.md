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
**Production: Google Gemini. Testing: Groq.**
- All scripts use `LLMClient` from `scripts/llm_client.py` — never call Anthropic or any other provider directly
- Production default: `gemini/gemini-2.0-flash` (15 RPM, 1,500 RPD)
- Testing default: `groq/llama-3.1-8b-instant` (30 RPM, 14,400 RPD — 10× quota, much faster)
- Do NOT add `anthropic` calls — the goal is a fully free pipeline
- If a new script needs an LLM call, always use `LLMClient().chat(prompt, max_tokens=N)`
- Override model via `LLM_MODEL` env var; override test model via `TEST_LLM_MODEL`

## Environment Variables (.env)
```
GOOGLE_API_KEY=        # Required for production — https://aistudio.google.com/apikey
GROQ_API_KEY=          # Required for testing   — https://console.groq.com/keys  (free)
SERPAPI_KEY=           # Required for job search (screen_jobs.py)
LLM_MODEL=             # Optional — override production model
TEST_LLM_MODEL=        # Optional — override model used when rebuilding test cache
```

## Current Next Step
All 6 stages built + Streamlit UI. Testing infrastructure in place (53 unit tests passing).

**START HERE TOMORROW — Claude CLI provider (unlocks unlimited free testing):**
1. Add a `claude-cli` provider to `scripts/llm_client.py` that shells out to `claude -p "prompt"` via subprocess
2. Add env var `LLM_PROVIDER=claude-cli` (or `TEST_LLM_PROVIDER=claude-cli`) to `.env`
3. Verify integration tests pass with this provider: `make test-integration`
4. Verify the Streamlit UI works end-to-end using this provider (run `streamlit run app.py`)
5. Once claude-cli testing confirms the full pipeline works, get Groq API key as the production-testing default

**Why:** Marcus has Claude Code Pro subscription — `claude` CLI is already installed and authenticated, zero extra API keys needed, unlimited calls. This unblocks all integration + UI testing immediately.

**Streamlit UI connection idea:** The Streamlit app already calls all scripts via `llm_client.py`. Setting `LLM_PROVIDER=claude-cli` in `.env` before launching `streamlit run app.py` should make the entire UI use the claude-cli provider automatically — no UI changes needed.

**After that:**
- Privacy audit — verify `.gitignore` covers all PII (see PLAN.md)
