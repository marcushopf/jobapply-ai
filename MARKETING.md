# jobapply-ai — Marketing & Positioning

> Not a build priority. Revisit after testing is complete and the tool is stable.
> This file is the source of truth for positioning, USPs, and go-to-market thinking.

---

## The One-Sentence Pitch

> **"Answer 10 targeted questions once. Get tailored CVs and cover letters for every job in your shortlist — for free."**

The interview is the mechanism; the output (better, personalized applications at no cost) is the value.

---

## Who is the Target User?

**Primary:** Technical job seekers (developers, PMs, data roles) who are comfortable running a local app but frustrated paying $30–50/month for tools that just mass-apply the same CV everywhere.

**Secondary (stretch):** Non-technical job seekers — only reachable if the Streamlit UI is packaged so there's no Python/venv/`.env` setup required (Docker image or hosted version).

**Not the target:** Recruiters and agencies. They already use Recruit CRM, Loxo, Greenhouse. The multi-candidate architecture is a clean implementation detail, not a product differentiator for this audience.

---

## USP Ranking — By Real User Impact

| Rank | USP | Why it moves users |
|------|-----|--------------------|
| 1 | **Free** — Gemini free tier, no subscription | Removes the #1 barrier to trying anything |
| 2 | **Quality over quantity** — gap-driven tailoring per job | Differentiates from LoopCV/LazyApply mass-apply tools |
| 3 | **One interview → many applications** — answer once, apply many | Concrete time saving with higher quality output |
| 4 | **Privacy / local** — all data stays on your machine | Meaningful niche: EU/GDPR users, sensitive roles |
| 5 | **Fit report** — per-role score + gap-closing roadmap | Career planning bonus; not primary for "need a job now" users |

**Removed from moat list:** Multi-candidate. It's an architectural decision that keeps code clean, not something users care about.

---

## What No Existing Tool Does

1. **Gap-analysis-driven interview** — questions are derived from the actual delta between the candidate's CV and the shortlisted job descriptions. No competitor does this; all mock interviews are generic.
2. **Full pipeline, self-hosted & free** — discover → gap → interview → fit report → tailored application → LinkedIn optimiser, end-to-end, local, zero subscription cost.
3. **Privacy-first** — no CV uploaded to a third-party SaaS. Runs on Gemini free tier + Ollama local fallback.

The closest competitor combo is **AIApply** (document generation) + **Careerflow** (LinkedIn + generic mock interviews) used together — still missing gap-driven interview, fit report, and free local operation.

---

## Framing Problem to Solve Before Launch

The gap-driven interview could feel like friction ("you want to interview me before I can apply?"). The framing must lead with the output:

- **Wrong:** "We interview you first to understand your gaps."
- **Right:** "Answer 10 questions about your background once. The tool figures out what each employer needs to know and writes the application for you."

The interview is invisible infrastructure; the promise is: one setup session, then personalized applications on autopilot.

---

## What's Needed to Reach Non-Technical Users

1. Docker image or hosted Streamlit — no Python install, no `.env` file, no venv
2. "Free" must be front and center in README/landing page, not buried in docs
3. The one-sentence pitch above as the README headline

These are launch-phase concerns, not build-phase concerns.
