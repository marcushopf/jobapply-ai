# JobApply AI — Build Plan

## The Funnel

```
Upload CVs → Parse Profile → Fill Wishlist → Screen & Shortlist Jobs →
Gap Analysis → Targeted Interview → Fit Report → Generate Applications → Track
```

## Stages

### Stage 1: CV Ingestion & Profile Extraction
- Candidate uploads one or more CV files (PDF, DOCX, TXT) to `candidates/[id]/cvs/`
- Claude parses all CVs and merges into a structured `candidates/[id]/profile.json`
- Flags what's present and what's missing
- Supports multiple candidates — each has their own isolated folder

### Stage 1b: Wishlist Setup
- Interactive CLI captures what the candidate actually wants
- Dream job titles, also-open-to titles, target industries, locations
- Remote preference, company size, target companies, salary range
- Must-haves and deal-breakers
- Saved to `candidates/[id]/wishlist.json`
- Feeds directly into job search queries and scoring

### Stage 2: Job Discovery & Screening
- Reads candidate preferences and skills from `profile.json`
- Calls Adzuna API to fetch relevant job listings
- Scores each listing against the candidate profile (match score 0–100)
- Saves shortlisted jobs to `candidates/[id]/job_screenings/`
- Status flow: `screened` → `shortlisted` | `skipped`
- Full funnel: e.g. 40 screened → 10 shortlisted

### Stage 3: Gap Analysis
- Compares shortlisted job descriptions against the candidate's parsed profile
- Identifies what information is missing or underspecified that jobs require
- Produces a `gap_report.json` per candidate: which questions need to be asked
- This drives the interview — no generic questions, only relevant ones

### Stage 4: Targeted Interview Bot
- Reads `gap_report.json` — only asks questions relevant to the shortlisted jobs
- One question at a time
- Saves answers back into `profile.json` to enrich it
- Saves session transcript to `candidates/[id]/interviews/session_NNN.md`
- Updates `tracker.json` when profile is sufficiently complete

### Stage 4b: Fit Report
- Scores the candidate against each target job title (not just specific listings)
- Reply probability per role: high / medium / low / very low
- Visual score bar for each title
- Deep dream job analysis: current gaps, how to close them, timeline, stepping stones
- Saved to `candidates/[id]/fit_report.json`

### Stage 5: Application Generator
- For each shortlisted job: generates tailored CV + cover letter using Claude API
- Uses enriched `profile.json` + specific job description
- Saves to `candidates/[id]/applications/[app_id]/`:
  - `cover_letter.md`
  - `cv_tailored.md`
  - `meta.json`
- Updates `tracker.json` with application status

**TODO: CV Template & Formatting**
- Research best CV examples for specific roles (PM, engineer, etc.)
- Build an ATS-safe CV template (clean Markdown → PDF)
- Template should be role-aware: PM CVs emphasise outcomes, engineering CVs emphasise stack/impact
- Auto-format the tailored CV output so it's always professional without manual design work
- Candidate should never need to touch a design tool

## Folder Structure

```
jobapply-ai/
├── PLAN.md
├── CLAUDE.md
├── question_bank/
│   └── questions.json          # Interview questions by job category
└── candidates/
    └── [candidate_id]/         # e.g. jane_doe
        ├── tracker.json        # Per-candidate state — read first every session
        ├── profile.json        # Merged, enriched candidate profile
        ├── gap_report.json     # Gaps between profile and shortlisted jobs
        ├── cvs/                # Uploaded CV files (PDF, DOCX, TXT)
        ├── interviews/         # Session transcripts (session_001.md, etc.)
        ├── job_screenings/
        │   ├── screening_log.json
        │   └── details/        # Per-job screening details
        └── applications/
            └── app_NNN_company/
                ├── cover_letter.md
                ├── cv_tailored.md
                └── meta.json
```

## Tech Stack
| Layer        | Choice                          |
|--------------|---------------------------------|
| AI backbone  | Claude API (claude-sonnet-4-6)  |
| Storage      | GitHub repo (jobapply-ai)       |
| Job listings | Adzuna API (free tier)          |
| Runtime      | Python (CLI scripts)            |
| CV parsing   | Claude API + pdfplumber / python-docx |

## Build Status

> This is the single source of truth for project progress.
> Check this file at the start of every session to know what's done and what's next.

- [x] Scope defined
- [x] Folder structure initialized (multi-candidate)
- [x] Repo pushed to GitHub
- [x] Stage 1: CV ingestion & profile extraction (`scripts/ingest_cvs.py`)
- [x] Stage 1b: Wishlist setup — dream jobs, industries, salary, must-haves (`scripts/setup_wishlist.py`)
- [x] Stage 2: Job discovery & screening via SerpAPI/Google Jobs (`scripts/screen_jobs.py`)
- [ ] Stage 3: Gap analysis — compare profile vs. shortlisted job descriptions (`scripts/gap_analysis.py`)
- [ ] Stage 4: Targeted interview bot — only asks what's missing for real jobs (`scripts/interview.py`)
- [x] Stage 4b: Fit report — score vs. each target title + dream job deep analysis (`scripts/fit_report.py`)
- [ ] Stage 5: Application generator — tailored CV + cover letter per job (`scripts/generate_application.py`)
- [ ] Stage 5b: CV template & ATS-safe formatting (role-aware, Markdown → PDF, no design tool needed)
