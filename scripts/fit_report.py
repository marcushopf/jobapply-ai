#!/usr/bin/env python3
"""
Stage 4b: Fit Report Generator

After the interview enriches the candidate profile, this script scores the
candidate against each of their target job titles and generates a detailed
fit report — including reply probability and a dream job gap analysis.

Usage:
    python scripts/fit_report.py --candidate jane_doe

Output:
    candidates/[id]/fit_report.json
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
        sys.exit(f"Candidate not found: {candidate_id}")
    return d


def reply_probability(score: int) -> str:
    if score >= 80:
        return "high"
    if score >= 60:
        return "medium"
    if score >= 40:
        return "low"
    return "very low"


def probability_label(score: int) -> str:
    labels = {
        "high": "Strong match — likely to get a reply (>80%)",
        "medium": "Decent match — good chance of a reply (50-80%)",
        "low": "Partial match — possible reply if you tailor well (20-50%)",
        "very low": "Weak match — unlikely without significant upskilling (<20%)",
    }
    return labels[reply_probability(score)]


# ---------------------------------------------------------------------------
# Claude scoring
# ---------------------------------------------------------------------------

def score_job_title(title: str, profile: dict, wishlist: dict,
                    client: anthropic.Anthropic) -> dict:
    """Score candidate fitness for a generic job title (not a specific listing)."""

    prompt = f"""You are a senior recruiter assessing a candidate's fit for a job title.

Candidate Profile:
{json.dumps(profile, indent=2)}

Target Job Title: "{title}"

Assess how well this candidate fits the typical requirements for "{title}" roles
in the current market (especially European job market).

Return ONLY valid JSON, no explanation:
{{
  "fit_score": 72,
  "reply_probability": "medium",
  "strengths": [
    "Strong background in X which is core to this role",
    "Experience at Y-type companies aligns well"
  ],
  "gaps": [
    "Missing direct experience with Z, which is commonly required",
    "Portfolio/case studies not evident from CV"
  ],
  "quick_wins": [
    "Highlight X more prominently in CV",
    "Add metrics to Y experience"
  ],
  "summary": "One paragraph honest assessment of this candidate for this role."
}}

Be honest and specific. fit_score is 0-100. reply_probability is one of: high, medium, low, very low."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

    return json.loads(raw)


def dream_job_deep_analysis(dream_title: str, profile: dict, wishlist: dict,
                             fit: dict, client: anthropic.Anthropic) -> dict:
    """Deep analysis for the candidate's #1 dream job."""

    prompt = f"""You are a senior career coach doing a deep assessment for a candidate's dream job.

Candidate Profile:
{json.dumps(profile, indent=2)}

Candidate Wishlist:
{json.dumps(wishlist, indent=2)}

Dream Job Title: "{dream_title}"
Current Fit Score: {fit['fit_score']}/100

Give an honest, actionable deep analysis of what it would take for this candidate
to land their dream role. Be specific, encouraging but realistic.

Return ONLY valid JSON:
{{
  "current_fit": {fit['fit_score']},
  "what_they_have": [
    "Concrete strength 1 that directly helps for this dream role",
    "Concrete strength 2"
  ],
  "critical_gaps": [
    {{
      "gap": "What is missing",
      "why_it_matters": "Why this blocks the dream role",
      "how_to_close": "Specific action to close this gap",
      "effort": "weeks | months | years"
    }}
  ],
  "immediate_actions": [
    "Action they can take this week",
    "Action they can take this month"
  ],
  "realistic_timeline": "Honest estimate of how long to be competitive for this role",
  "stepping_stone_roles": [
    "Intermediate role 1 that builds toward the dream job",
    "Intermediate role 2"
  ],
  "motivational_note": "One honest, encouraging sentence for the candidate."
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

    return json.loads(raw)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate fit report for a candidate")
    parser.add_argument("--candidate", required=True, help="Candidate ID (e.g. jane_doe)")
    args = parser.parse_args()

    candidate_id = args.candidate
    base = candidate_dir(candidate_id)

    profile = load_json(base / "profile.json")
    wishlist_path = base / "wishlist.json"
    wishlist = json.loads(wishlist_path.read_text()) if wishlist_path.exists() else {}

    if not wishlist:
        print("No wishlist found. Run setup_wishlist.py first for best results.")
        print("Continuing with profile data only...\n")

    client = anthropic.Anthropic()

    # Collect all target titles
    all_titles = wishlist.get("dream_jobs", []) + wishlist.get("also_open_to", [])
    if not all_titles:
        exp = profile.get("experience", [])
        all_titles = [exp[0]["title"]] if exp else ["Software Engineer"]

    dream_title = all_titles[0]

    print(f"Generating fit report for: {profile.get('name', candidate_id)}")
    print(f"Target roles: {all_titles}")
    print(f"Dream job: {dream_title}\n")

    # Score each target title
    title_fits = []
    for title in all_titles:
        print(f"  Scoring: {title}...", end=" ", flush=True)
        fit = score_job_title(title, profile, wishlist, client)
        fit["title"] = title
        fit["probability_label"] = probability_label(fit["fit_score"])
        title_fits.append(fit)
        score = fit["fit_score"]
        prob = fit["reply_probability"]
        print(f"score: {score}/100 ({prob} reply probability)")

    # Deep analysis for dream job
    print(f"\n  Deep analysis for dream job: {dream_title}...")
    dream_fit = next((f for f in title_fits if f["title"] == dream_title), title_fits[0])
    dream_analysis = dream_job_deep_analysis(dream_title, profile, wishlist, dream_fit, client)

    # Build report
    report = {
        "candidate": profile.get("name", candidate_id),
        "generated": date.today().isoformat(),
        "dream_job": dream_title,
        "job_title_fits": title_fits,
        "dream_job_analysis": dream_analysis,
        "summary": {
            "best_fit_role": max(title_fits, key=lambda x: x["fit_score"])["title"],
            "best_fit_score": max(title_fits, key=lambda x: x["fit_score"])["fit_score"],
            "dream_job_score": dream_fit["fit_score"],
            "dream_job_probability": dream_fit["reply_probability"],
        },
    }

    report_path = base / "fit_report.json"
    report_path.write_text(json.dumps(report, indent=2))

    print(f"\nFit report saved: {report_path}")
    print("\n" + "="*60)
    print("  FIT REPORT SUMMARY")
    print("="*60)

    for fit in sorted(title_fits, key=lambda x: x["fit_score"], reverse=True):
        bar = "█" * (fit["fit_score"] // 10) + "░" * (10 - fit["fit_score"] // 10)
        print(f"  {fit['title']:<35} {bar} {fit['fit_score']:>3}/100  ({fit['reply_probability']})")

    print(f"\n  Dream job: {dream_title}")
    print(f"  Timeline: {dream_analysis.get('realistic_timeline', 'n/a')}")
    print(f"\n  Immediate actions:")
    for action in dream_analysis.get("immediate_actions", [])[:3]:
        print(f"    • {action}")

    print(f"\n  \"{dream_analysis.get('motivational_note', '')}\"")
    print("="*60)


if __name__ == "__main__":
    main()
