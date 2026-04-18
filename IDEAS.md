# JobApply AI — Ideas & Inspiration

> Drop anything here: new feature ideas, course notes, links, observations,
> things to research. At the start of a session, scan this file for items
> worth moving into PLAN.md as a concrete improvement stage.

---

## Feature Ideas

<!-- Add new ideas below. Format: idea, why it matters, rough effort (small/medium/large) -->

- [ ] Integrate LinkedIn Learning / course content to strengthen interview answers and CV language
- [ ] Auto-detect tone of a job description (formal/startup/corporate) and match cover letter tone
- [ ] Add a "rejection analyser" — if a candidate gets rejected, learn from the pattern
- [ ] Email/calendar integration — track interview dates and follow-up reminders
- [ ] Multi-language support — generate CVs and cover letters in German, French, etc.
- [ ] Salary benchmarking — pull market salary data per role/location to advise the candidate

---

## Inspiration & Resources

<!-- Courses, articles, books, tools worth exploring -->

### LinkedIn Learning — A Career Strategist's Guide to Getting a Job
Source: https://www.linkedin.com/learning/a-career-strategist-s-guide-to-getting-a-job

**Table of Contents:**

1. Start a job search
   - Create a career plan
   - Identify a target job
   - Use informational interviews to your advantage

2. Find available jobs
   - Find the right job postings
   - How to attract or find the right recruiters
   - How to enlist a network to find a job
   - How to get "ins" at companies of interest

3. Prepare to apply for a job
   - How to craft a professional brand
   - How to write a cover letter
   - How to write a resume
   - How to get a resume through the ATS

4. How to interview like a pro
   - How to prepare for a job interview
   - How to succeed in a job interview
   - How to salvage a botched interview
   - How to follow up after a job interview

5. Negotiate, negotiate, negotiate
   - How to negotiate salary
   - How to negotiate benefits

6. Start a new job strong
   - How to succeed in the first 60 days of a job

---

**Analysis — what's relevant for JobApply AI:**

| Topic | Relevance | Current status | Potential feature |
|---|---|---|---|
| Create a career plan | High | Wishlist covers this partially | Extend wishlist with longer-term career goals |
| Identify a target job | High | Done — wishlist + fit report | Already covered |
| Informational interviews | Medium | Not covered | Track networking conversations per target company |
| Find the right job postings | High | Done — SerpAPI/Google Jobs | Already covered |
| Attract / find recruiters | High | Not covered | Generate tailored LinkedIn profile copy (headline, summary, skills, keywords) → candidate pastes manually. Note: LinkedIn API does not allow automated profile updates. |
| Enlist a network | Medium | Not covered | Network tracker — who do you know at target companies? |
| Get "ins" at companies | Medium | Not covered | Target company research module — news, culture, key people |
| Craft a professional brand | High | Partial — CV + cover letter | Add LinkedIn profile optimisation suggestions as output |
| Write a cover letter | High | Done — Stage 5 | Already covered |
| Write a resume / CV | High | Done — Stage 5 | Already covered |
| Get resume through ATS | High | Stage 5b TODO | ATS-safe formatting — already planned |
| Prepare for interview | High | Not covered | **Interview prep module** — generates likely questions per job + suggested answers based on profile |
| Succeed in interview | High | Not covered | Part of interview prep module |
| Salvage a botched interview | Low | Not covered | Parking lot |
| Follow up after interview | Medium | Not covered | Follow-up email generator + reminder |
| Negotiate salary | High | Not covered | Salary negotiation brief — market data + talking points per offer |
| Negotiate benefits | Medium | Not covered | Part of salary negotiation module |
| First 60 days | Low | Out of scope | Parking lot — post-hire, not job search |

**Priority items to graduate to PLAN.md (Phase 2):**
1. **Interview prep module** — generate likely interview questions per job + suggested answers (high impact, directly extends our flow)
2. **LinkedIn profile optimisation** — output a suggested LinkedIn summary/headline based on enriched profile + target roles
3. **Follow-up email generator** — after an interview, generate a professional follow-up email
4. **Salary negotiation brief** — when an offer comes, generate a negotiation brief with market data and talking points
5. **Network tracker** — track who the candidate knows at target companies, prompt them to reach out

### Articles & Links
<!-- Useful links go here -->

---

## Observations & Feedback

<!-- Things noticed during testing, candidate feedback, things that didn't work well -->

---

## Parking Lot

<!-- Good ideas but not the right time — revisit later -->

