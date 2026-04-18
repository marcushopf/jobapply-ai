# JobApply AI — Claude Code Instructions

## What This Project Is
A smart job application agent that interviews the user once, then applies to many jobs on their behalf — fully tailored per job, fully tracked.

## Start of Every Session
1. Read `tracker.json` — understand current state (profile completeness, sessions run, jobs screened, applications sent)
2. Read `candidate/profile.json` — know what we already know about the candidate
3. Read `PLAN.md` — check which stages are complete
4. Never repeat work already done (e.g. don't re-ask interview questions already answered)

## Key Rules
- `tracker.json` is the single source of truth — always update it after any action
- One question at a time during interviews — never overwhelm the user
- All generated files go in the correct folders (see PLAN.md for structure)
- Adzuna API key stored in `.env` (never commit this file)
- Claude API key stored in `.env` (never commit this file)

## Folder Structure
```
jobapply-ai/
├── tracker.json          # Central state — read first every session
├── PLAN.md               # Build plan and stage status
├── CLAUDE.md             # This file
├── candidate/
│   ├── profile.json      # Structured candidate profile
│   └── interviews/       # Session transcripts (session_001.md, etc.)
├── job_screenings/
│   ├── screening_log.json
│   └── details/          # Per-job screening details
├── applications/
│   └── app_NNN_company/  # cover_letter.md, cv_tailored.md, meta.json
└── question_bank/
    └── questions.json    # Interview questions by job category
```

## Current Next Step
Build the interview bot (Stage 1). It should:
- Read tracker.json to find known_gaps and profile_completeness
- Ask targeted questions to fill gaps
- Save output to candidate/profile.json and candidate/interviews/
