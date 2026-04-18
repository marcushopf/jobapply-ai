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

## Environment Variables (.env)
```
ANTHROPIC_API_KEY=
ADZUNA_APP_ID=
ADZUNA_APP_KEY=
```

## Current Next Step
Build Stage 1: CV ingestion script (`scripts/ingest_cvs.py`)
- Takes a candidate name + CV file paths as input
- Creates the candidate folder structure
- Parses CVs using Claude API
- Writes structured output to `candidates/[id]/profile.json`
