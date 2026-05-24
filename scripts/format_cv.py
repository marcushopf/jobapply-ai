#!/usr/bin/env python3
"""
Stage 5b: CV Formatter

Takes a tailored CV (Markdown) and produces a clean, ATS-safe HTML file.
Role-aware: adapts emphasis for PM, engineering, data, or management roles.
Open the HTML in a browser and use File → Print → Save as PDF.

Usage:
    python scripts/format_cv.py --candidate jane_doe
    python scripts/format_cv.py --candidate jane_doe --app app_001_booking_com_senior_manager
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from llm_client import LLMClient
from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# ATS-safe HTML template
# ---------------------------------------------------------------------------

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} — CV</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: Arial, Helvetica, sans-serif;
    font-size: 10.5pt;
    line-height: 1.45;
    color: #000;
    background: #fff;
    max-width: 780px;
    margin: 0 auto;
    padding: 2cm 2cm 2.5cm 2cm;
  }}
  h1 {{ font-size: 20pt; font-weight: 700; margin-bottom: 4px; }}
  h2 {{
    font-size: 11.5pt; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.05em; border-bottom: 1.5px solid #000;
    margin-top: 18px; margin-bottom: 8px; padding-bottom: 3px;
  }}
  h3 {{ font-size: 10.5pt; font-weight: 700; margin-top: 10px; margin-bottom: 2px; }}
  h4 {{ font-size: 10.5pt; font-weight: 400; font-style: italic; margin-bottom: 4px; }}
  p {{ margin-bottom: 5px; }}
  ul {{ padding-left: 18px; margin-bottom: 6px; }}
  li {{ margin-bottom: 2px; }}
  strong {{ font-weight: 700; }}
  em {{ font-style: italic; }}
  a {{ color: #000; text-decoration: none; }}
  @media print {{
    body {{ padding: 1.5cm; font-size: 10pt; }}
    h2 {{ page-break-after: avoid; }}
    h3 {{ page-break-after: avoid; }}
  }}
</style>
</head>
<body>
{body}
</body>
</html>"""


# ---------------------------------------------------------------------------
# Role detection
# ---------------------------------------------------------------------------

ROLE_GUIDANCE = {
    "product": (
        "Emphasise product outcomes, user impact, business metrics, and strategic decisions. "
        "Lead each role with the business problem solved and measurable outcome. "
        "Highlight roadmap ownership, stakeholder alignment, and cross-functional leadership. "
        "De-emphasise technical implementation details."
    ),
    "engineering": (
        "Emphasise technical stack, system design, scale/performance metrics, and engineering impact. "
        "Lead each role with technical achievements. Include specific technologies prominently in skills. "
        "Show progression from individual contributor to senior/lead where applicable."
    ),
    "data": (
        "Balance technical depth with business impact. Emphasise analytical methods, data scale, "
        "model performance metrics, and insights delivered. Include specific tools and frameworks. "
        "Show how data work influenced decisions and outcomes."
    ),
    "management": (
        "Lead with leadership impact: team size, org changes, people development, and strategic "
        "initiatives. Emphasise cross-functional influence and business outcomes driven. "
        "De-emphasise individual technical contributions in favour of organisational impact."
    ),
    "general": (
        "Emphasise transferable skills, measurable achievements, and career progression. "
        "Balance technical and business impact. Show clear growth trajectory."
    ),
}


def detect_role_type(job_title: str, wishlist: dict) -> str:
    all_titles = [job_title] + wishlist.get("dream_jobs", []) + wishlist.get("also_open_to", [])
    text = " ".join(all_titles).lower()

    if any(k in text for k in ["product manager", " pm ", "head of product", "vp product",
                                 "product director", "product lead", "chief product"]):
        return "product"
    if any(k in text for k in ["engineer", "developer", "software", "backend", "frontend",
                                 "fullstack", "devops", "sre", "platform"]):
        return "engineering"
    if any(k in text for k in ["data scien", "machine learning", " ml ", " ai ", "analytics",
                                 "analyst", "data lead", "data manager", "data director"]):
        return "data"
    if any(k in text for k in ["manager", "director", "head of", " vp ", "vice president",
                                 "chief", " cto", " cpo", " cdo", "senior manager"]):
        return "management"
    return "general"


# ---------------------------------------------------------------------------
# LLM: reformat and optimise
# ---------------------------------------------------------------------------

def reformat_cv(cv_markdown: str, role_type: str, job_title: str, company: str,
                client: LLMClient) -> str:
    guidance = ROLE_GUIDANCE[role_type]

    prompt = f"""You are formatting a tailored CV for a job application.

Target job: {job_title} at {company}
Role type: {role_type}
Formatting guidance: {guidance}

Current CV (Markdown):
{cv_markdown}

Rewrite and reformat this CV as clean Markdown following these rules:
1. Apply the formatting guidance above — reorder bullets, strengthen language, surface the right metrics.
2. Structure: Name (# heading), contact line, then sections as ## headings.
3. Each experience: ### Company — Title (h3), dates as plain text on next line, bullet points.
4. Skills section: group into 3-4 categories (e.g. Leadership · Technical · Tools · Languages).
5. Keep it factual — never invent details. Only reframe what is already there.
6. Every bullet must start with a strong action verb.
7. ATS rules: no tables, no columns, no icons, no special characters beyond standard punctuation.
8. Length: 1–2 pages (roughly 600–900 words of content).

Return clean Markdown only — no explanation, no code fences."""

    return client.chat(prompt, max_tokens=2048)


# ---------------------------------------------------------------------------
# Markdown → HTML
# ---------------------------------------------------------------------------

def md_to_html(md_text: str, candidate_name: str) -> str:
    try:
        import markdown as md_lib
        body = md_lib.markdown(md_text, extensions=["nl2br"])
    except ImportError:
        # Basic fallback: wrap paragraphs in <p> tags
        lines = md_text.split("\n")
        html_lines = []
        for line in lines:
            if line.startswith("# "):
                html_lines.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith("## "):
                html_lines.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("### "):
                html_lines.append(f"<h3>{line[4:]}</h3>")
            elif line.startswith("- "):
                html_lines.append(f"<li>{line[2:]}</li>")
            elif line.strip():
                html_lines.append(f"<p>{line}</p>")
        body = "\n".join(html_lines)

    return HTML_TEMPLATE.format(name=candidate_name, body=body)


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


def get_app_dirs(base: Path, app_filter: str | None) -> list[Path]:
    apps_dir = base / "applications"
    if not apps_dir.exists():
        sys.exit("No applications found. Run generate_application.py first.")
    dirs = [
        d for d in sorted(apps_dir.iterdir())
        if d.is_dir() and (d / "cv_tailored.md").exists() and (d / "meta.json").exists()
    ]
    if app_filter:
        dirs = [d for d in dirs if d.name == app_filter]
    if not dirs:
        sys.exit("No matching applications found.")
    return dirs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Format tailored CVs into ATS-safe HTML")
    parser.add_argument("--candidate", required=True, help="Candidate ID (e.g. jane_doe)")
    parser.add_argument("--app", help="Process a specific app folder only (e.g. app_001_booking_com)")
    args = parser.parse_args()

    candidate_id = args.candidate
    base = candidate_dir(candidate_id)

    profile = load_json(base / "profile.json")
    wishlist_path = base / "wishlist.json"
    wishlist = json.loads(wishlist_path.read_text()) if wishlist_path.exists() else {}
    candidate_name = profile.get("name", candidate_id)

    app_dirs = get_app_dirs(base, args.app)
    client = LLMClient()

    print(f"\n{'='*60}")
    print(f"  CV FORMATTER — {candidate_name.upper()}")
    print(f"{'='*60}")
    print(f"  Applications to format: {len(app_dirs)}")
    print(f"{'='*60}\n")

    for app_dir in app_dirs:
        meta = json.loads((app_dir / "meta.json").read_text())
        job_title = meta["title"]
        company = meta["company"]

        role_type = detect_role_type(job_title, wishlist)
        print(f"[{meta['app_id']}] {job_title} @ {company} (role type: {role_type})")

        cv_md = (app_dir / "cv_tailored.md").read_text()

        print(f"  Reformatting for {role_type} role...", end=" ", flush=True)
        cv_formatted_md = reformat_cv(cv_md, role_type, job_title, company, client)
        (app_dir / "cv_formatted.md").write_text(cv_formatted_md)
        print("done")

        print(f"  Converting to HTML...", end=" ", flush=True)
        html = md_to_html(cv_formatted_md, candidate_name)
        html_path = app_dir / "cv_formatted.html"
        html_path.write_text(html)
        print("done")

        print(f"  Saved: {html_path}")
        print(f"  Open in browser → File → Print → Save as PDF\n")

    print(f"{'='*60}")
    print(f"  {len(app_dirs)} CV(s) formatted")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
