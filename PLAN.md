# JobApply AI — Build Plan

## The Funnel
Interview → Auto-Screen & Score → Shortlist → Tailor & Generate → Apply → Track Outcome

## Stages

### Stage 1: Interview Bot (next to build)
- Reads `tracker.json` at start — skips already-covered topics
- Asks one question at a time to extract candidate profile
- Saves profile to `candidate/profile.json`
- Saves session transcript to `candidate/interviews/session_NNN.md`
- Updates `tracker.json` with session details and profile completeness

### Stage 2: Job Discovery & Screening
- Reads candidate preferences from `candidate/profile.json`
- Calls Adzuna API to fetch job listings
- Scores each job against candidate profile (0–100 match score)
- Logs results to `job_screenings/screening_log.json` and `job_screenings/details/`
- Status flow: `screened` → `shortlisted` | `skipped`

### Stage 3: Application Generator
- For each shortlisted job: generates tailored CV + cover letter using Claude API
- Saves to `applications/[app_id]/`:
  - `cover_letter.md`
  - `cv_tailored.md`
  - `meta.json`
- Updates `tracker.json` application status

### Stage 4: Tracker & Reporting
- `tracker.json` is the single source of truth
- Full funnel visibility: screened → shortlisted → applied → interviews → offers

## Tech Stack
| Layer        | Choice                          |
|--------------|---------------------------------|
| AI backbone  | Claude API (claude-sonnet-4-6)  |
| Storage      | GitLab repo (jobapply-ai)       |
| Job listings | Adzuna API (free tier)          |
| Runtime      | Python (CLI scripts)            |

## Status
- [x] Scope defined
- [x] Folder structure initialized
- [ ] Interview bot built
- [ ] Job screener built
- [ ] Application generator built
