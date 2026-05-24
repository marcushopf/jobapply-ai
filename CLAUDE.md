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
**This project uses Google Gemini via LiteLLM as the sole LLM provider.**
- All scripts import `LLMClient` from `scripts/llm_client.py` — never call Anthropic or any other provider directly
- Default model: `gemini/gemini-2.0-flash` (free tier via Google AI Studio)
- Do NOT add `anthropic` calls or suggest switching to Anthropic — the goal is a fully free pipeline
- If a new script needs an LLM call, always use `LLMClient().chat(prompt, max_tokens=N)`
- Override model via `LLM_MODEL` env var if needed

## Environment Variables (.env)
```
GOOGLE_API_KEY=        # Required — get free key at https://aistudio.google.com/apikey
SERPAPI_KEY=           # Required for job search (screen_jobs.py)
LLM_MODEL=             # Optional — override default gemini/gemini-2.0-flash
```

## Current Next Step
Build Stage 5b: ATS-safe CV formatting (`scripts/generate_application.py` already done).
- Research best CV templates for PM / data / engineering roles
- Role-aware Markdown → PDF pipeline (no design tool needed)
