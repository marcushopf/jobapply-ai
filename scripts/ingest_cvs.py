#!/usr/bin/env python3
"""
Stage 1: CV Ingestion & Profile Extraction

Usage:
    python scripts/ingest_cvs.py --name "Jane Doe" --cvs path/to/cv1.pdf path/to/cv2.pdf

What it does:
    1. Creates candidates/[id]/ folder structure
    2. Copies CV files into candidates/[id]/cvs/
    3. Extracts text from each CV (PDF, DOCX, TXT)
    4. Sends all CV text to Claude API to merge into a structured profile
    5. Writes candidates/[id]/profile.json
    6. Updates candidates/[id]/tracker.json
"""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path

import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).parent))

from llm_client import LLMClient
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def candidate_id_from_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def candidate_dir(candidate_id: str) -> Path:
    return Path("data/candidates") / candidate_id


def ensure_structure(candidate_id: str) -> Path:
    base = candidate_dir(candidate_id)
    for sub in ["cvs", "interviews", "job_screenings/details", "applications"]:
        (base / sub).mkdir(parents=True, exist_ok=True)
    return base


def extract_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()

    if suffix == ".txt":
        return file_path.read_text(encoding="utf-8", errors="ignore")

    if suffix == ".pdf":
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                return "\n".join(
                    page.extract_text() or "" for page in pdf.pages
                )
        except ImportError:
            sys.exit("pdfplumber not installed. Run: pip install pdfplumber")

    if suffix in (".docx", ".doc"):
        try:
            import docx
            doc = docx.Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            sys.exit("python-docx not installed. Run: pip install python-docx")

    sys.exit(f"Unsupported file type: {suffix}. Supported: pdf, docx, txt")


def parse_profile_with_claude(cv_texts: list[tuple[str, str]], candidate_name: str) -> dict:
    """Send all CV texts to the LLM and get back a structured profile."""
    client = LLMClient()

    cv_blocks = "\n\n".join(
        f"--- CV: {filename} ---\n{text}" for filename, text in cv_texts
    )

    prompt = f"""You are parsing CV documents for a job application system.

Candidate name: {candidate_name}

Below are one or more CV documents (possibly different versions or years).
Extract and merge all information into a single structured JSON profile.
Use the most recent/complete information where there are conflicts.

CVs:
{cv_blocks}

Return ONLY valid JSON matching this exact schema — no markdown, no explanation:
{{
  "name": "",
  "email": "",
  "phone": "",
  "location": "",
  "summary": "",
  "skills": ["skill1", "skill2"],
  "experience": [
    {{
      "title": "",
      "company": "",
      "location": "",
      "start_date": "",
      "end_date": "",
      "current": false,
      "description": ""
    }}
  ],
  "education": [
    {{
      "degree": "",
      "field": "",
      "institution": "",
      "graduation_year": ""
    }}
  ],
  "languages": [
    {{"language": "", "level": ""}}
  ],
  "certifications": [],
  "preferences": {{
    "job_titles": [],
    "locations": [],
    "remote": null,
    "salary_min": null,
    "industries": []
  }},
  "cv_sources": [],
  "parsed_date": "{date.today().isoformat()}"
}}"""

    raw = client.chat(prompt, max_tokens=4096).strip()
    # Strip markdown code fences if Claude added them
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

    return json.loads(raw)


def init_tracker(candidate_id: str, candidate_name: str) -> dict:
    return {
        "candidate_id": candidate_id,
        "name": candidate_name,
        "stage": "cvs_ingested",
        "profile_completeness": 0,
        "known_gaps": [],
        "last_updated": date.today().isoformat(),
        "interview_sessions": [],
        "job_screenings": [],
        "applications": [],
        "question_bank_version": "1.0",
    }


def update_candidates_index(candidate_id: str, candidate_name: str):
    index_path = Path("data/candidates/index.json")
    index = json.loads(index_path.read_text()) if index_path.exists() else {"candidates": {}}
    index["candidates"][candidate_id] = {
        "name": candidate_name,
        "created": date.today().isoformat(),
    }
    index_path.write_text(json.dumps(index, indent=2))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Ingest CV files for a candidate")
    parser.add_argument("--name", required=True, help='Candidate full name, e.g. "Jane Doe"')
    parser.add_argument("--cvs", nargs="+", required=True, help="Paths to CV files (PDF/DOCX/TXT)")
    args = parser.parse_args()

    candidate_name = args.name
    candidate_id = candidate_id_from_name(candidate_name)
    cv_paths = [Path(p) for p in args.cvs]

    # Validate files exist
    for p in cv_paths:
        if not p.exists():
            sys.exit(f"File not found: {p}")

    print(f"Candidate: {candidate_name} (id: {candidate_id})")
    print(f"CVs to ingest: {[str(p) for p in cv_paths]}")

    # Create folder structure
    base = ensure_structure(candidate_id)
    print(f"Created folder structure: {base}/")

    # Copy CVs into candidates/[id]/cvs/
    cv_texts = []
    for cv_path in cv_paths:
        dest = base / "cvs" / cv_path.name
        try:
            shutil.copy2(cv_path, dest)
            print(f"Copied: {cv_path.name}")
        except shutil.SameFileError:
            print(f"Already in place: {cv_path.name}")
        text = extract_text(cv_path)
        cv_texts.append((cv_path.name, text))

    # Parse with LLM
    print("Parsing CVs...")
    profile = parse_profile_with_claude(cv_texts, candidate_name)
    profile["cv_sources"] = [p.name for p in cv_paths]

    # Estimate completeness
    filled = sum(1 for k in ["name", "email", "phone", "location", "summary"]
                 if profile.get(k))
    filled += min(len(profile.get("skills", [])), 5)
    filled += min(len(profile.get("experience", [])), 3)
    completeness = min(int((filled / 13) * 100), 100)

    # Write profile
    profile_path = base / "profile.json"
    profile_path.write_text(json.dumps(profile, indent=2))
    print(f"Profile written: {profile_path}")

    # Write tracker
    tracker = init_tracker(candidate_id, candidate_name)
    tracker["profile_completeness"] = completeness
    tracker_path = base / "tracker.json"
    tracker_path.write_text(json.dumps(tracker, indent=2))
    print(f"Tracker written: {tracker_path}")

    # Update global index
    update_candidates_index(candidate_id, candidate_name)

    print(f"\nDone. Profile completeness: {completeness}%")
    print(f"Next step: run job screening for {candidate_id}")


if __name__ == "__main__":
    main()
