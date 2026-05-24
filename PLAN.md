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
- Flags whats present and whats missing
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
- Compares shortlisted job descriptions against the candidates parsed profile
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
- Auto-format the tailored CV output so its always professional without manual design work
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

## Testing Checklist

> Run `make test` before every commit (unit tests, no LLM, fast).
> Run `make test-integration` before any release (real Gemini calls).
> Run `make test-e2e` for a full pipeline smoke-test (Alex Müller → N26 job).
> UI testing is manual — use the Streamlit checklist below.

### Unit Tests — `make test` (fast, no LLM)
- [ ] `test_ingest.py` — candidate ID generation, text extraction
- [ ] `test_screening.py` — score threshold, job ID, slugify, search queries
- [ ] `test_format_cv.py` — role type detection, HTML output shape
- [ ] `test_utils.py` — JSON fence stripping, stage rank order, wishlist parsing

### Integration Tests — `make test-integration` (real Gemini API)
- [ ] `test_gap_analysis.py` — gap schema valid, priorities valid, resolved=false
- [ ] `test_applications.py` — cover letter length, no placeholders, company name present
- [ ] `test_linkedin.py` — headline ≤220 chars, exactly 50 skills, About in first person

### End-to-End — `make test-e2e` (full pipeline, ~5 min)
- [ ] Stage 1: profile.json created with name, experience, skills
- [ ] Stage 1b: wishlist.json saved
- [ ] Stage 2: job scored 0–100, saved to job_screenings/details/
- [ ] Stage 3: gap_report.json has ≥1 gap for Alex vs N26
- [ ] Stage 4: interview enriches profile with interview_additions
- [ ] Stage 4b: fit_report.json has fit_score 0–100
- [ ] Stage 5: cover_letter.md + cv_tailored.md generated, mention N26
- [ ] Stage 5b: cv_formatted.html valid, contains @media print
- [ ] Stage 6: linkedin_profile.md has all sections, 50 skills, headline ≤220

### Streamlit UI — manual checklist (run after any significant change)
- [ ] API key setup page appears when no key in keychain
- [ ] New candidate created from Home, appears in sidebar dropdown
- [ ] CV file upload extracts profile correctly
- [ ] Wishlist form saves all fields
- [ ] Manual job add scores the job and shows shortlisted/skipped
- [ ] Gap analysis runs and shows gaps by priority (🔴🟡🟢)
- [ ] Interview chat advances one question at a time, skip button works
- [ ] Fit report shows score bars per role
- [ ] Applications generate with download buttons for cover letter + CV
- [ ] Format CV produces HTML, download button works
- [ ] LinkedIn profile generates all sections, download button works
- [ ] Progress bar in sidebar updates at each stage

### Multi-Candidate Isolation
- [ ] Run pipeline for two candidates, verify no data crossover in tracker.json
- [ ] Each candidate's applications/ folder contains only their own documents

---

## Build Status

> This is the single source of truth for project progress.
> Check this file at the start of every session to know whats done and whats next.
> New ideas and inspiration live in IDEAS.md — review it each session and promote worthy items below.

### Phase 1 — Initial Build
- [x] Scope defined
- [x] Folder structure initialized (multi-candidate)
- [x] Repo pushed to GitHub
- [x] Stage 1: CV ingestion & profile extraction (`scripts/ingest_cvs.py`)
- [x] Stage 1b: Wishlist setup — dream jobs, industries, salary, must-haves (`scripts/setup_wishlist.py`)
- [x] Stage 2: Job discovery & screening via SerpAPI/Google Jobs (`scripts/screen_jobs.py`)
- [x] Stage 3: Gap analysis — compare profile vs. shortlisted job descriptions (`scripts/gap_analysis.py`)
- [x] Stage 4: Targeted interview bot — only asks whats missing for real jobs (`scripts/interview.py`)
- [x] Stage 4b: Fit report — score vs. each target title + dream job deep analysis (`scripts/fit_report.py`)
- [x] Stage 4c: Multi-provider LLM support — `scripts/llm_client.py` (LiteLLM wrapper, Gemini free tier default). All scripts updated.
- [x] Stage 5: Application generator — tailored CV + cover letter per job (`scripts/generate_application.py`)
- [x] Streamlit UI — full web interface wrapping all stages (`app.py`)
- [x] Stage 5b: CV template & ATS-safe formatting — role-aware reformat → clean HTML → print to PDF (`scripts/format_cv.py`)
- [x] Stage 6: LinkedIn profile optimiser — headline, About, 50 skills, experience rewrites, Open to Work settings (`scripts/linkedin_profile.py`) → `candidates/[id]/linkedin_profile.md`
- [ ] Privacy audit — verify `.gitignore` covers all personal data (`data/`, CVs, profiles, gap reports, interview transcripts, applications); confirm no PII has ever been committed to GitHub

### Phase 2 — Continuous Improvement
> Items graduate here from IDEAS.md once scoped and prioritised.
> Each improvement gets a checkbox when done.

- [ ] _(next improvement — promote from IDEAS.md)_

---

> **How to add an improvement:**
> 1. Drop the idea into `IDEAS.md` first (free-form, no pressure)
> 2. When ready to build, move it here as a `- [ ]` item with a short description
> 3. Tick it off `- [x]` when done
