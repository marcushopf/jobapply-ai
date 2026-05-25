#!/usr/bin/env python3
"""
Stage 5: Application Generator

Generates a tailored CV and cover letter for each shortlisted job using the
enriched candidate profile (including interview additions).

Usage:
    python scripts/generate_application.py --candidate jane_doe
    python scripts/generate_application.py --candidate jane_doe --job job_001
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from llm_client import LLMClient
from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path: Path) -> dict:
    if not path.exists():
        sys.exit(f"File not found: {path}")
    return json.loads(path.read_text())


def candidate_dir(candidate_id: str) -> Path:
    d = Path("data/candidates") / candidate_id
    if not d.exists():
        sys.exit(f"Candidate not found: {candidate_id}\nRun ingest_cvs.py first.")
    return d


def load_shortlisted_jobs(candidate_id: str, job_filter: str | None = None) -> list[dict]:
    details_dir = Path("data/candidates") / candidate_id / "job_screenings" / "details"
    if not details_dir.exists():
        sys.exit("No job screenings found. Run screen_jobs.py first.")

    jobs = []
    for f in sorted(details_dir.glob("*.json")):
        job = json.loads(f.read_text())
        if job.get("status") != "shortlisted":
            continue
        job_id = job.get("id") or job.get("job_id")
        if job_filter and job_id != job_filter:
            continue
        jobs.append(job)

    if not jobs:
        msg = f"No shortlisted job found with id '{job_filter}'." if job_filter else "No shortlisted jobs found."
        sys.exit(msg)

    return jobs


def next_app_number(apps_dir: Path) -> int:
    nums = []
    for d in apps_dir.iterdir():
        m = re.match(r"app_(\d+)", d.name)
        if m:
            nums.append(int(m.group(1)))
    return max(nums) + 1 if nums else 1


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower())[:30].strip("_")


def strip_fences(text: str) -> str:
    text = re.sub(r"^```[a-z]*\n?", "", text.strip())
    text = re.sub(r"\n?```$", "", text).strip()
    for start, end in [("[", "]"), ("{", "}")]:
        s, e = text.find(start), text.rfind(end)
        if s != -1 and e > s:
            return text[s:e + 1]
    return text


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def generate_cover_letter(job: dict, profile: dict, client: LLMClient) -> str:
    desc = job.get("description", "")
    if isinstance(desc, dict):
        desc = json.dumps(desc)

    additions = profile.get("interview_additions", [])
    additions_text = ""
    if additions:
        additions_text = "\n\nInterview additions (enriched details):\n" + json.dumps(additions, indent=2)[:2000]

    prompt = f"""You are writing a tailored cover letter for a job application.

Candidate Profile:
{json.dumps({k: profile.get(k) for k in ['name', 'summary', 'skills', 'experience', 'education', 'languages']}, indent=2)[:3000]}
{additions_text}

Target Job:
Title: {job['title']}
Company: {job['company']}
Description: {desc[:2500]}

Write a professional, compelling cover letter (3–4 paragraphs):
1. Opening: Why this specific role and company excites the candidate — be specific, not generic.
2. Core match: 2–3 strongest points of fit with concrete evidence and metrics where available.
3. Added value: What they uniquely bring to this team.
4. Close: Professional sign-off with a clear call to action.

Rules:
- Tone: professional but human, confident not arrogant.
- Length: 300–400 words.
- No placeholders or [brackets] — this must be ready to send.
- Do not invent facts. Only use information from the profile.
- Output clean Markdown only (no extra explanation)."""

    return client.chat(prompt, max_tokens=1024)


def generate_tailored_cv(job: dict, profile: dict, client: LLMClient) -> str:
    desc = job.get("description", "")
    if isinstance(desc, dict):
        desc = json.dumps(desc)

    additions = profile.get("interview_additions", [])
    additions_text = ""
    if additions:
        additions_text = "\n\nInterview additions (use these to enrich experience descriptions):\n" + json.dumps(additions, indent=2)[:2000]

    prompt = f"""You are writing a tailored CV for a job application.

Candidate Profile:
{json.dumps(profile, indent=2)[:4000]}
{additions_text}

Target Job:
Title: {job['title']}
Company: {job['company']}
Description: {desc[:2500]}

Write a tailored CV in clean Markdown. Rules:
- Lead with the most relevant experience for this role.
- Incorporate specific metrics and evidence from interview additions where they strengthen the match.
- Naturally weave in keywords from the job description — do not keyword-stuff.
- Never invent facts. Only use information from the profile.
- ATS-safe format: no tables, no columns, no icons or special characters.
- Sections: Summary, Skills, Experience, Education, Languages.
- Keep it to 1–2 pages worth of content.
- Output clean Markdown only (no extra explanation)."""

    return client.chat(prompt, max_tokens=2048)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate tailored applications for shortlisted jobs")
    parser.add_argument("--candidate", required=True, help="Candidate ID (e.g. jane_doe)")
    parser.add_argument("--job", help="Generate for a single job ID only (e.g. job_001)")
    args = parser.parse_args()

    candidate_id = args.candidate
    base = candidate_dir(candidate_id)

    profile = load_json(base / "profile.json")
    jobs = load_shortlisted_jobs(candidate_id, args.job)

    apps_dir = base / "applications"
    apps_dir.mkdir(exist_ok=True)

    client = LLMClient()

    print(f"\n{'='*60}")
    print(f"  APPLICATION GENERATOR — {profile.get('name', candidate_id).upper()}")
    print(f"{'='*60}")
    print(f"  Jobs to process: {len(jobs)}")
    print(f"  Provider: {client.provider} ({client.model})")
    print(f"{'='*60}\n")

    generated = []

    for job in jobs:
        job_id = job.get("id") or job.get("job_id")
        app_num = next_app_number(apps_dir)
        folder_name = f"app_{app_num:03d}_{slugify(job['company'])}_{slugify(job['title'])}"
        app_dir = apps_dir / folder_name
        app_dir.mkdir(exist_ok=True)

        print(f"[{job_id}] {job['title']} @ {job['company']}")

        print(f"  Generating cover letter...", end=" ", flush=True)
        cover_letter = generate_cover_letter(job, profile, client)
        (app_dir / "cover_letter.md").write_text(cover_letter)
        print("done")

        print(f"  Generating tailored CV...", end=" ", flush=True)
        cv = generate_tailored_cv(job, profile, client)
        (app_dir / "cv_tailored.md").write_text(cv)
        print("done")

        meta = {
            "app_id": folder_name,
            "job_id": job_id,
            "title": job["title"],
            "company": job["company"],
            "generated_date": date.today().isoformat(),
            "status": "draft",
        }
        (app_dir / "meta.json").write_text(json.dumps(meta, indent=2))

        print(f"  Saved: {app_dir}/\n")
        generated.append(meta)

    # Update tracker
    tracker_path = base / "tracker.json"
    tracker = json.loads(tracker_path.read_text()) if tracker_path.exists() else {}
    tracker["stage"] = "applications_generated"
    tracker.setdefault("applications", []).extend(generated)
    tracker["last_updated"] = date.today().isoformat()
    tracker_path.write_text(json.dumps(tracker, indent=2))

    print(f"{'='*60}")
    print(f"  {len(generated)} application(s) generated")
    for g in generated:
        print(f"  • {g['title']} @ {g['company']}  →  {g['app_id']}/")
    print(f"\n  Review and send:")
    print(f"  data/candidates/{candidate_id}/applications/")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
