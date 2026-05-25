#!/usr/bin/env python3
"""
Stage 6: LinkedIn Profile Optimiser

Generates a complete, keyword-optimised LinkedIn profile based on the
enriched candidate profile, wishlist, and fit report.
Output is a ready-to-copy-paste Markdown file.

Usage:
    python scripts/linkedin_profile.py --candidate jane_doe
"""

import argparse
import json
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
        sys.exit(f"Candidate not found: {candidate_id}")
    return d


def strip_fences(text: str) -> str:
    import re
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

def generate_headline(profile: dict, wishlist: dict, client: LLMClient) -> str:
    target_titles = wishlist.get("dream_jobs", []) + wishlist.get("also_open_to", [])

    prompt = f"""Write a LinkedIn headline for this candidate.

Candidate name: {profile.get('name', '')}
Current/most recent role: {profile.get('experience', [{}])[0].get('title', '')} at {profile.get('experience', [{}])[0].get('company', '')}
Target roles: {', '.join(target_titles[:3])}
Key skills: {', '.join(profile.get('skills', [])[:10])}

Rules:
- Max 120 characters (LinkedIn limit)
- Keyword-rich: include target job title + 1-2 key skills
- Human and specific — not a list of buzzwords
- Do NOT use pipes excessively — max 2 separators
- Do NOT start with "I am" or "Passionate"
- Return only the headline text, nothing else."""

    return client.chat(prompt, max_tokens=100).strip()


def generate_about(profile: dict, wishlist: dict, fit_report: dict, client: LLMClient) -> str:
    target_titles = wishlist.get("dream_jobs", []) + wishlist.get("also_open_to", [])
    best_role = fit_report.get("summary", {}).get("best_fit_role", target_titles[0] if target_titles else "")

    prompt = f"""Write a LinkedIn About section for this candidate.

Profile:
{json.dumps({k: profile.get(k) for k in ['name', 'summary', 'skills', 'experience']}, indent=2)[:3000]}

Target roles: {', '.join(target_titles[:3])}
Best fit role: {best_role}
Target industries: {', '.join(wishlist.get('target_industries', []))}

Rules:
- 250–350 words
- First line must be a hook — bold claim or compelling statement (no "I am a...")
- Tell a career story: where you came from → what you do best → where you're heading
- Include 5-8 keywords naturally (recruiter search terms for the target role)
- End with a clear call to action ("Open to [role] opportunities in [location]" or similar)
- Write in first person, professional but human tone
- No bullet points — flowing paragraphs only
- Return the About text only, no explanation."""

    return client.chat(prompt, max_tokens=600).strip()


def generate_skills_section(profile: dict, wishlist: dict, fit_report: dict,
                             client: LLMClient) -> list[str]:
    target_titles = wishlist.get("dream_jobs", []) + wishlist.get("also_open_to", [])

    prompt = f"""Generate a LinkedIn skills list for this candidate.

Profile skills: {', '.join(profile.get('skills', []))}
Target roles: {', '.join(target_titles[:3])}
Target industries: {', '.join(wishlist.get('target_industries', []))}
Experience: {json.dumps([{k: e.get(k) for k in ['title', 'company', 'description']} for e in profile.get('experience', [])[:4]], indent=2)[:2000]}

Rules:
- Return at least 60 skills (we will trim to 50, so generate more than enough)
- Mix: hard skills (tools, methods, technologies) + soft skills + domain knowledge
- Prioritise skills that match the target roles and show up in job descriptions
- Order: most important/differentiating first
- Return ONLY a JSON array of strings, no explanation:
["Skill 1", "Skill 2", ...]"""

    raw = strip_fences(client.chat(prompt, max_tokens=2048))
    skills = json.loads(raw)

    # Top-up if the model returned fewer than 50
    if len(skills) < 50:
        needed = 50 - len(skills)
        existing_lower = {s.lower() for s in skills}
        topup_prompt = (
            f"Generate {needed + 10} more unique LinkedIn skills for a {', '.join(target_titles[:2])} "
            f"that are NOT already in this list: {json.dumps(skills)}. "
            f"Return ONLY a JSON array of strings."
        )
        try:
            extra_raw = strip_fences(client.chat(topup_prompt, max_tokens=512))
            extras = [s for s in json.loads(extra_raw) if s.lower() not in existing_lower]
            skills = skills + extras
        except Exception:
            pass

    return skills[:50]


def generate_experience_descriptions(profile: dict, wishlist: dict,
                                     client: LLMClient) -> list[dict]:
    target_titles = wishlist.get("dream_jobs", []) + wishlist.get("also_open_to", [])

    prompt = f"""Rewrite experience descriptions for LinkedIn.

Target roles the candidate is pursuing: {', '.join(target_titles[:3])}

Current experience:
{json.dumps(profile.get('experience', []), indent=2)[:3000]}

Interview additions (extra context):
{json.dumps(profile.get('interview_additions', []), indent=2)[:1500]}

For each role, write a LinkedIn-optimised description:
- 2-4 bullet points starting with strong action verbs
- Lead with the most impressive achievement or scope
- Include metrics where available
- Naturally include keywords relevant to the target roles
- Keep each bullet to 1-2 lines (LinkedIn truncates long descriptions)
- Never invent facts — only use what is in the profile

Return ONLY a JSON array, one object per role (in same order as input):
[
  {{
    "title": "same title as input",
    "company": "same company as input",
    "description": "• Bullet 1\\n• Bullet 2\\n• Bullet 3"
  }}
]"""

    raw = strip_fences(client.chat(prompt, max_tokens=2048))
    return json.loads(raw)


def generate_open_to_work(profile: dict, wishlist: dict) -> dict:
    return {
        "job_titles": (wishlist.get("dream_jobs", []) + wishlist.get("also_open_to", []))[:5],
        "locations": wishlist.get("target_locations", []),
        "job_types": _infer_job_types(wishlist),
        "start_date": "Immediately" if not wishlist.get("notice_period") else wishlist.get("notice_period"),
        "visibility": "All LinkedIn members (recommended for active search)",
    }


def _infer_job_types(wishlist: dict) -> list[str]:
    remote = wishlist.get("remote_preference", "flexible")
    types = ["Full-time"]
    if remote in ("remote", "flexible"):
        types.append("Remote")
    if remote in ("hybrid", "flexible"):
        types.append("Hybrid")
    return types


def generate_featured_suggestions(profile: dict, wishlist: dict, client: LLMClient) -> list[str]:
    prompt = f"""Suggest what this candidate should put in their LinkedIn Featured section.

Profile: {json.dumps({k: profile.get(k) for k in ['summary', 'experience', 'skills']}, indent=2)[:2000]}
Target roles: {', '.join(wishlist.get('dream_jobs', [])[:3])}

LinkedIn Featured section can include: posts, articles, links, media, documents.
Suggest 3-5 specific, actionable items this candidate should create or add.
Each suggestion should be concrete (e.g. "Write a LinkedIn article about X based on your experience at Y").

Return ONLY a JSON array of strings:
["Suggestion 1", "Suggestion 2"]"""

    raw = strip_fences(client.chat(prompt, max_tokens=400))
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Assemble output document
# ---------------------------------------------------------------------------

def build_profile_doc(
    headline: str,
    about: str,
    skills: list[str],
    experience_descriptions: list[dict],
    open_to_work: dict,
    featured: list[str],
    candidate_name: str,
) -> str:
    skills_rows = [skills[i:i+5] for i in range(0, min(len(skills), 50), 5)]
    skills_text = "\n".join(" · ".join(row) for row in skills_rows)

    exp_text = ""
    for exp in experience_descriptions:
        exp_text += f"\n### {exp['title']} — {exp['company']}\n\n{exp['description']}\n"

    oto = open_to_work
    oto_titles = "\n".join(f"  - {t}" for t in oto.get("job_titles", []))
    oto_locations = "\n".join(f"  - {l}" for l in oto.get("locations", []))
    oto_types = ", ".join(oto.get("job_types", []))

    featured_text = "\n".join(f"- {s}" for s in featured)

    return f"""# LinkedIn Profile — {candidate_name}
*Generated: {date.today().isoformat()}*
*Copy-paste each section directly into LinkedIn.*

---

## Headline
*(120 char max — paste into Profile > Headline)*

{headline}

---

## About
*(paste into Profile > About)*

{about}

---

## Skills
*(add via Profile > Skills — top 50 recommended)*

{skills_text}

---

## Experience Descriptions
*(edit each role via Profile > Experience)*
{exp_text}

---

## Open to Work Settings
*(set via Profile photo > Open to Work)*

**Job titles to list:**
{oto_titles}

**Preferred locations:**
{oto_locations}

**Job types:** {oto_types}
**Start date:** {oto.get("start_date", "Immediately")}
**Visibility:** {oto.get("visibility", "All LinkedIn members")}

---

## Featured Section Ideas
*(add via Profile > Add profile section > Featured)*

{featured_text}

---

*Tip: After updating your profile, turn on "Open to Work" and post a brief update
announcing you're exploring new opportunities — posts get 5-10x more views than profile-only changes.*
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate LinkedIn profile for a candidate")
    parser.add_argument("--candidate", required=True, help="Candidate ID (e.g. jane_doe)")
    args = parser.parse_args()

    candidate_id = args.candidate
    base = candidate_dir(candidate_id)

    profile = load_json(base / "profile.json")
    wishlist_path = base / "wishlist.json"
    wishlist = json.loads(wishlist_path.read_text()) if wishlist_path.exists() else {}
    fit_path = base / "fit_report.json"
    fit_report = json.loads(fit_path.read_text()) if fit_path.exists() else {}

    candidate_name = profile.get("name", candidate_id)
    client = LLMClient()

    print(f"\n{'='*60}")
    print(f"  LINKEDIN PROFILE — {candidate_name.upper()}")
    print(f"{'='*60}\n")

    print("  Generating headline...", end=" ", flush=True)
    headline = generate_headline(profile, wishlist, client)
    print("done")

    print("  Generating About section...", end=" ", flush=True)
    about = generate_about(profile, wishlist, fit_report, client)
    print("done")

    print("  Generating skills list (50)...", end=" ", flush=True)
    skills = generate_skills_section(profile, wishlist, fit_report, client)
    print("done")

    print("  Rewriting experience descriptions...", end=" ", flush=True)
    experience_descriptions = generate_experience_descriptions(profile, wishlist, client)
    print("done")

    print("  Building Open to Work settings...", end=" ", flush=True)
    open_to_work = generate_open_to_work(profile, wishlist)
    print("done")

    print("  Generating Featured section ideas...", end=" ", flush=True)
    featured = generate_featured_suggestions(profile, wishlist, client)
    print("done")

    doc = build_profile_doc(
        headline, about, skills, experience_descriptions,
        open_to_work, featured, candidate_name,
    )

    output_path = base / "linkedin_profile.md"
    output_path.write_text(doc)

    # Update tracker
    tracker_path = base / "tracker.json"
    tracker = json.loads(tracker_path.read_text()) if tracker_path.exists() else {}
    tracker["linkedin_profile_generated"] = date.today().isoformat()
    tracker["last_updated"] = date.today().isoformat()
    tracker_path.write_text(json.dumps(tracker, indent=2))

    print(f"\n{'='*60}")
    print(f"  LinkedIn profile saved: {output_path}")
    print(f"{'='*60}")
    print(f"\n  Sections generated:")
    print(f"  • Headline ({len(headline)} chars)")
    print(f"  • About ({len(about.split())} words)")
    print(f"  • {len(skills)} skills")
    print(f"  • {len(experience_descriptions)} experience descriptions")
    print(f"  • Open to Work settings")
    print(f"  • {len(featured)} Featured section ideas")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
