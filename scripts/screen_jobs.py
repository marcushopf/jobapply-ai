#!/usr/bin/env python3
"""
Stage 2: Job Discovery & Screening

Usage:
    # Auto-search via Google Jobs (SerpAPI)
    python scripts/screen_jobs.py --candidate jane_doe

    # Search with custom query override
    python scripts/screen_jobs.py --candidate jane_doe --query "Senior Product Manager Berlin"

    # Add a job manually (paste URL or description)
    python scripts/screen_jobs.py --candidate jane_doe --manual

What it does:
    1. Reads candidate profile to build search queries
    2. Searches Google Jobs via SerpAPI (aggregates LinkedIn, StepStone, Glassdoor, etc.)
    3. Scores each job against the candidate profile using Claude (0-100)
    4. Saves all results to candidates/[id]/job_screenings/
    5. Shortlists jobs scoring >= threshold (default: 60)
    6. Updates candidates/[id]/tracker.json
"""

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).parent))

from llm_client import LLMClient
from dotenv import load_dotenv

load_dotenv()

SHORTLIST_THRESHOLD = 60
MAX_RESULTS_PER_QUERY = 10


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_profile(candidate_id: str) -> dict:
    path = Path("data/candidates") / candidate_id / "profile.json"
    if not path.exists():
        sys.exit(f"Profile not found: {path}\nRun ingest_cvs.py first.")
    return json.loads(path.read_text())


def load_wishlist(candidate_id: str) -> dict:
    path = Path("data/candidates") / candidate_id / "wishlist.json"
    return json.loads(path.read_text()) if path.exists() else {}


def load_tracker(candidate_id: str) -> dict:
    path = Path("data/candidates") / candidate_id / "tracker.json"
    return json.loads(path.read_text()) if path.exists() else {}


def save_tracker(candidate_id: str, tracker: dict):
    path = Path("data/candidates") / candidate_id / "tracker.json"
    tracker["last_updated"] = date.today().isoformat()
    path.write_text(json.dumps(tracker, indent=2))


def screening_dir(candidate_id: str) -> Path:
    d = Path("data/candidates") / candidate_id / "job_screenings" / "details"
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_path(candidate_id: str) -> Path:
    return Path("data/candidates") / candidate_id / "job_screenings" / "screening_log.json"


def load_screening_log(candidate_id: str) -> dict:
    path = log_path(candidate_id)
    if path.exists():
        return json.loads(path.read_text())
    return {"screenings": []}


def save_screening_log(candidate_id: str, log: dict):
    log_path(candidate_id).write_text(json.dumps(log, indent=2))


def next_job_id(log: dict) -> str:
    existing = [s["id"] for s in log["screenings"]]
    n = len(existing) + 1
    return f"job_{n:03d}"


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower())[:40].strip("_")


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def build_search_queries(profile: dict, wishlist: dict) -> list[str]:
    """Build search queries from wishlist (primary) and profile (fallback)."""
    queries = []

    # Wishlist is the primary source
    all_titles = wishlist.get("dream_jobs", []) + wishlist.get("also_open_to", [])
    locations = wishlist.get("target_locations", [])

    # Fallback to profile preferences
    if not all_titles:
        prefs = profile.get("preferences", {})
        all_titles = prefs.get("job_titles", [])
        if not all_titles:
            exp = profile.get("experience", [])
            if exp:
                all_titles = [exp[0].get("title", "")]

    if not locations:
        prefs = profile.get("preferences", {})
        locations = prefs.get("locations", [profile.get("location", "")])

    # Build title x location combinations
    for title in all_titles[:3]:
        for location in locations[:2]:
            if title and location:
                queries.append(f"{title} {location}")
            elif title:
                queries.append(title)

    # Add target company searches for dream jobs
    target_companies = wishlist.get("target_companies", [])
    dream_title = all_titles[0] if all_titles else ""
    for company in target_companies[:2]:
        if dream_title:
            queries.append(f"{dream_title} {company}")

    return queries[:6] if queries else ["Software Engineer"]


def search_google_jobs(query: str, location: str = "") -> list[dict]:
    """Search Google Jobs via SerpAPI."""
    try:
        from serpapi import GoogleSearch
    except ImportError:
        sys.exit("serpapi not installed. Run: pip install google-search-results")

    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        sys.exit("SERPAPI_KEY not set in .env")

    params = {
        "engine": "google_jobs",
        "q": query,
        "api_key": api_key,
        "hl": "en",
        "num": MAX_RESULTS_PER_QUERY,
    }
    if location:
        params["location"] = location

    search = GoogleSearch(params)
    results = search.get_dict()
    jobs = results.get("jobs_results", [])

    normalized = []
    for j in jobs:
        normalized.append({
            "title": j.get("title", ""),
            "company": j.get("company_name", ""),
            "location": j.get("location", ""),
            "description": j.get("description", ""),
            "source": j.get("via", ""),
            "source_url": next(
                (ext.get("url", "") for ext in j.get("related_links", []) if ext.get("url")),
                ""
            ),
            "posted": j.get("detected_extensions", {}).get("posted_at", ""),
            "employment_type": j.get("detected_extensions", {}).get("schedule_type", ""),
        })
    return normalized


def get_manual_job() -> dict:
    """Prompt user to paste a job description or URL manually."""
    print("\nManual job entry")
    print("Paste the job URL or full job description, then press Enter twice when done:\n")

    lines = []
    while True:
        line = input()
        if line == "" and lines and lines[-1] == "":
            break
        lines.append(line)

    content = "\n".join(lines).strip()
    title = input("Job title: ").strip()
    company = input("Company name: ").strip()
    location = input("Location: ").strip()

    return {
        "title": title,
        "company": company,
        "location": location,
        "description": content,
        "source": "manual",
        "source_url": content if content.startswith("http") else "",
        "posted": date.today().isoformat(),
        "employment_type": "",
    }


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_job(job: dict, profile: dict, wishlist: dict, client: LLMClient) -> tuple[int, str]:
    """Score a job against a candidate profile using Claude. Returns (score, reasoning)."""

    prompt = f"""You are scoring a job listing against a candidate profile and their wishlist.

Candidate Profile:
{json.dumps(profile, indent=2)}

Candidate Wishlist (what they actually want):
{json.dumps(wishlist, indent=2)}

Job Listing:
Title: {job['title']}
Company: {job['company']}
Location: {job['location']}
Description: {job['description'][:2000]}

Score this job from 0 to 100 based on:
- Skills match (35 points): How well do the candidate's skills match the job requirements?
- Experience match (25 points): Does their experience level and background fit?
- Wishlist match (30 points): Does this job align with their dream roles, industries, location, remote preference, salary, must-haves? Penalise hard for deal-breakers.
- Growth potential (10 points): Is this a good career move toward their dream job?

Return ONLY valid JSON, no explanation:
{{
  "score": 75,
  "reasoning": "Strong skills match in X and Y. Experience level fits. Location matches preference. Missing Z which is listed as required."
}}"""

    raw = client.chat(prompt, max_tokens=512).strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

    result = json.loads(raw)
    return result["score"], result["reasoning"]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Screen jobs for a candidate")
    parser.add_argument("--candidate", required=True, help="Candidate ID (e.g. jane_doe)")
    parser.add_argument("--query", help="Override search query")
    parser.add_argument("--manual", action="store_true", help="Add a job manually")
    parser.add_argument("--threshold", type=int, default=SHORTLIST_THRESHOLD,
                        help=f"Minimum score to shortlist (default: {SHORTLIST_THRESHOLD})")
    args = parser.parse_args()

    candidate_id = args.candidate
    profile = load_profile(candidate_id)
    wishlist = load_wishlist(candidate_id)
    tracker = load_tracker(candidate_id)
    log = load_screening_log(candidate_id)
    client = LLMClient()

    if not wishlist:
        print("No wishlist found. It's recommended to set one up first:")
        print(f"  python scripts/setup_wishlist.py --candidate {candidate_id}")
        print("Continuing with profile preferences only...\n")

    # Collect jobs to screen
    jobs_to_screen = []

    if args.manual:
        jobs_to_screen.append(get_manual_job())
    else:
        queries = [args.query] if args.query else build_search_queries(profile, wishlist)
        print(f"Search queries: {queries}")

        seen_titles = {s["title"] + s["company"] for s in log["screenings"]}

        for query in queries:
            print(f"\nSearching: '{query}'...")
            results = search_google_jobs(query)
            print(f"  Found {len(results)} results")

            for job in results:
                key = job["title"] + job["company"]
                if key not in seen_titles:
                    jobs_to_screen.append(job)
                    seen_titles.add(key)
                else:
                    print(f"  Skipping duplicate: {job['title']} @ {job['company']}")

    print(f"\nScoring {len(jobs_to_screen)} new jobs...")

    shortlisted = []
    details_dir = screening_dir(candidate_id)

    for job in jobs_to_screen:
        job_id = next_job_id(log)
        print(f"  [{job_id}] {job['title']} @ {job['company']} — scoring...", end=" ", flush=True)

        score, reasoning = score_job(job, profile, wishlist, client)
        status = "shortlisted" if score >= args.threshold else "skipped"
        print(f"score: {score} → {status}")

        entry = {
            "id": job_id,
            "title": job["title"],
            "company": job["company"],
            "location": job["location"],
            "source": job["source"],
            "source_url": job["source_url"],
            "date_screened": date.today().isoformat(),
            "match_score": score,
            "status": status,
            "reasoning": reasoning,
        }

        log["screenings"].append(entry)

        # Save full job details
        detail_file = details_dir / f"{job_id}_{slugify(job['company'])}_{slugify(job['title'])}.json"
        detail_file.write_text(json.dumps({**entry, "description": job["description"]}, indent=2))

        if status == "shortlisted":
            shortlisted.append(entry)

    # Update log and tracker
    save_screening_log(candidate_id, log)

    total = len(log["screenings"])
    total_shortlisted = sum(1 for s in log["screenings"] if s["status"] == "shortlisted")
    total_skipped = sum(1 for s in log["screenings"] if s["status"] == "skipped")

    tracker["stage"] = "jobs_screened"
    tracker["job_screenings"] = log["screenings"]
    save_tracker(candidate_id, tracker)

    print(f"\nDone.")
    print(f"Funnel: {total} screened → {total_shortlisted} shortlisted → {total_skipped} skipped")

    if shortlisted:
        print(f"\nShortlisted jobs:")
        for j in shortlisted:
            print(f"  [{j['id']}] {j['title']} @ {j['company']} (score: {j['match_score']})")
        print(f"\nNext step: run gap analysis")
        print(f"  python scripts/gap_analysis.py --candidate {candidate_id}")
    else:
        print("\nNo jobs shortlisted. Try lowering --threshold or adjusting preferences in profile.json")


if __name__ == "__main__":
    main()
