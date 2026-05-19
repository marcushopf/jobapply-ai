#!/usr/bin/env python3
"""
Stage 3: Gap Analysis

Compares the candidate's profile against all shortlisted jobs and produces a
prioritised gap_report.json that drives the targeted interview in Stage 4.

Usage:
    python scripts/gap_analysis.py --candidate jane_doe

What it does:
    1. Loads profile.json + wishlist.json
    2. Loads all shortlisted jobs from job_screenings/details/
    3. Per job: asks Claude what profile information is missing or underspecified
    4. Aggregates raw gaps across all jobs into a deduplicated, prioritised list
    5. Writes candidates/[id]/gap_report.json
    6. Updates candidates/[id]/tracker.json
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

import anthropic
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


def load_shortlisted_jobs(candidate_id: str) -> list[dict]:
    details_dir = Path("data/candidates") / candidate_id / "job_screenings" / "details"
    if not details_dir.exists():
        sys.exit("No job screenings found. Run screen_jobs.py first.")

    jobs = []
    for f in sorted(details_dir.glob("*.json")):
        job = json.loads(f.read_text())
        if job.get("status") == "shortlisted":
            jobs.append(job)

    if not jobs:
        sys.exit("No shortlisted jobs found. Lower --threshold in screen_jobs.py or re-run screening.")

    return jobs


def strip_fences(text: str) -> str:
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


def save_tracker(candidate_id: str, tracker: dict):
    path = Path("data/candidates") / candidate_id / "tracker.json"
    tracker["last_updated"] = date.today().isoformat()
    path.write_text(json.dumps(tracker, indent=2))


# ---------------------------------------------------------------------------
# Pass 1: per-job gap extraction
# ---------------------------------------------------------------------------

def extract_gaps_for_job(job: dict, profile: dict, client: anthropic.Anthropic) -> list[dict]:
    """Ask Claude what's missing or underspecified in the profile for this specific job."""

    desc = job.get('description', '')
    if isinstance(desc, dict):
        desc = json.dumps(desc)
    desc = desc[:3000]

    prompt = f"""You are a recruiter reviewing a candidate's profile against a job description.

Candidate Profile:
{json.dumps(profile, indent=2)}

Job:
Title: {job['title']}
Company: {job['company']}
Description: {desc}

Identify gaps — things the job requires that are missing or too vague in the profile.
Only flag real gaps: missing skills, unquantified impact, missing context about experience depth,
unclear seniority signals, or missing preferences the job explicitly asks about.
Do NOT flag things the candidate clearly has.

Return ONLY a JSON array, no explanation:
[
  {{
    "category": "metrics | skills | experience | preferences | soft_skills",
    "description": "Brief description of what is missing or underspecified",
    "raw_question": "The specific question to ask the candidate to fill this gap"
  }}
]

Return an empty array [] if the profile already covers this job well."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = strip_fences(message.content[0].text)
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Pass 2: aggregate and prioritise
# ---------------------------------------------------------------------------

def synthesise_gap_report(
    raw_gaps_by_job: list[dict],
    profile: dict,
    wishlist: dict,
    client: anthropic.Anthropic,
) -> list[dict]:
    """Deduplicate and prioritise raw per-job gaps into a final interview-ready list."""

    prompt = f"""You are building a targeted interview plan for a job applicant.

Below are raw gaps identified per job. Your task:
1. Deduplicate overlapping gaps (same underlying issue mentioned across jobs)
2. Merge similar gaps into one clear gap with one interview question
3. Rank by priority: high = affects many jobs or is a critical blocker; medium = affects some jobs; low = minor or nice-to-have
4. Write one clear, specific, open-ended interview question per gap
5. List which job IDs each gap affects

Raw gaps per job:
{json.dumps(raw_gaps_by_job, indent=2)}

Candidate Profile (for context):
{json.dumps(profile, indent=2)}

Return ONLY a JSON array, no explanation. Each item:
{{
  "gap_id": "gap_001",
  "category": "metrics | skills | experience | preferences | soft_skills",
  "description": "Clear description of what is missing",
  "affected_jobs": ["job_001", "job_003"],
  "question": "Specific, open-ended interview question to fill this gap",
  "priority": "high | medium | low",
  "resolved": false
}}

Order by priority descending (high first). Use gap_001, gap_002, ... IDs."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = strip_fences(message.content[0].text)
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Run gap analysis for a candidate")
    parser.add_argument("--candidate", required=True, help="Candidate ID (e.g. jane_doe)")
    args = parser.parse_args()

    candidate_id = args.candidate
    base = candidate_dir(candidate_id)

    profile = load_json(base / "profile.json")
    wishlist_path = base / "wishlist.json"
    wishlist = json.loads(wishlist_path.read_text()) if wishlist_path.exists() else {}

    jobs = load_shortlisted_jobs(candidate_id)
    client = anthropic.Anthropic()

    print(f"Candidate: {profile.get('name', candidate_id)}")
    print(f"Shortlisted jobs to analyse: {len(jobs)}\n")

    # Pass 1: extract gaps per job
    raw_gaps_by_job = []
    for job in jobs:
        job_id = job.get("id") or job.get("job_id")
        print(f"  [{job_id}] {job['title']} @ {job['company']} — extracting gaps...", end=" ", flush=True)
        gaps = extract_gaps_for_job(job, profile, client)
        print(f"{len(gaps)} gap(s) found")
        if gaps:
            raw_gaps_by_job.append({"job_id": job_id, "title": job["title"], "company": job["company"], "gaps": gaps})

    if not raw_gaps_by_job:
        print("\nNo gaps found — profile already covers all shortlisted jobs well.")
        gap_report = {
            "candidate_id": candidate_id,
            "generated_date": date.today().isoformat(),
            "jobs_analyzed": [j.get("id") or j.get("job_id") for j in jobs],
            "gaps": [],
            "counts": {"high": 0, "medium": 0, "low": 0, "total": 0},
            "summary": "No significant gaps identified. Profile covers all shortlisted jobs well.",
        }
    else:
        # Pass 2: synthesise into prioritised gap report
        print(f"\nSynthesising gaps across all jobs...")
        gaps = synthesise_gap_report(raw_gaps_by_job, profile, wishlist, client)

        counts = {
            "high": sum(1 for g in gaps if g["priority"] == "high"),
            "medium": sum(1 for g in gaps if g["priority"] == "medium"),
            "low": sum(1 for g in gaps if g["priority"] == "low"),
            "total": len(gaps),
        }

        gap_report = {
            "candidate_id": candidate_id,
            "generated_date": date.today().isoformat(),
            "jobs_analyzed": [j.get("id") or j.get("job_id") for j in jobs],
            "gaps": gaps,
            "counts": counts,
            "summary": f"{counts['total']} gaps identified: {counts['high']} high, {counts['medium']} medium, {counts['low']} low priority.",
        }

    # Write report
    report_path = base / "gap_report.json"
    report_path.write_text(json.dumps(gap_report, indent=2))
    print(f"\nGap report saved: {report_path}")

    # Update tracker
    tracker_path = base / "tracker.json"
    tracker = json.loads(tracker_path.read_text()) if tracker_path.exists() else {}
    tracker["stage"] = "gap_analysis_done"
    tracker["gap_report"] = {
        "generated_date": gap_report["generated_date"],
        "jobs_analyzed": len(jobs),
        **gap_report["counts"],
    }
    save_tracker(candidate_id, tracker)

    # Summary
    print("\n" + "=" * 55)
    print("  GAP ANALYSIS SUMMARY")
    print("=" * 55)
    print(f"  Jobs analysed:  {len(jobs)}")
    print(f"  Total gaps:     {gap_report['counts']['total']}")
    print(f"  High priority:  {gap_report['counts']['high']}")
    print(f"  Medium priority:{gap_report['counts']['medium']}")
    print(f"  Low priority:   {gap_report['counts']['low']}")

    if gap_report["gaps"]:
        print("\n  Gaps to cover in interview:")
        for g in gap_report["gaps"]:
            marker = "(!)" if g["priority"] == "high" else "   "
            jobs_str = ", ".join(g["affected_jobs"])
            print(f"  {marker} [{g['gap_id']}] {g['description'][:60]}")
            print(f"       affects: {jobs_str}")

    print("=" * 55)
    print(f"\nNext step: run the targeted interview")
    print(f"  python scripts/interview.py --candidate {candidate_id}")


if __name__ == "__main__":
    main()
