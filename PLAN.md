# JobApply AI — Build Plan

## The Funnel

```
Upload CVs → Parse Profile → Screen & Shortlist Jobs →
Gap Analysis → Targeted Interview → Generate Applications → Track
```

## Stages

### Stage 1: CV Ingestion & Profile Extraction
- Candidate uploads one or more CV files (PDF, DOCX, TXT) to `candidates/[id]/cvs/`
- Claude parses all CVs and merges into a structured `candidates/[id]/profile.json`
- Flags what's present and what's missing
- Supports multiple candidates — each has their own isolated folder

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

### Stage 5: Application Generator
- For each shortlisted job: generates tailored CV + cover letter using Claude API
- Uses enriched `profile.json` + specific job description
- Saves to `candidates/[id]/applications/[app_id]/`:
  - `cover_letter.md`
  - `cv_tailored.md`
  - `meta.json`
- Updates `tracker.json` with application status

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
- [x] Scope defined
- [x] Folder structure initialized
- [x] Repo pushed to GitHub
- [ ] Stage 1: CV ingestion & profile extraction
- [ ] Stage 2: Job discovery & screening
- [ ] Stage 3: Gap analysis
- [ ] Stage 4: Targeted interview bot
- [ ] Stage 5: Application generator
