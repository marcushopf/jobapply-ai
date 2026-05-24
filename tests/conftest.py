"""
Shared pytest fixtures and configuration.

Tests must be run from the project root:
    make test
    .venv/bin/pytest tests/unit/ -v
"""

import json
import os
import shutil
import sys
from datetime import date
from pathlib import Path

import pytest

# Make scripts and tests/ importable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

# ── Constants ──────────────────────────────────────────────────────────────

TEST_CANDIDATE_ID = "test_alex_muller"
TEST_CANDIDATE_NAME = "Alex Müller"
FIXTURES_DIR = Path(__file__).parent / "fixtures"
DATA_DIR = Path("data/candidates")


# ── Helpers ────────────────────────────────────────────────────────────────

def has_api_key() -> bool:
    if os.getenv("GOOGLE_API_KEY", "").strip():
        return True
    try:
        import keyring
        return bool(keyring.get_password("jobapply-ai", "google_api_key"))
    except Exception:
        return False


requires_api = pytest.mark.skipif(
    not has_api_key(),
    reason="No GOOGLE_API_KEY found — skipping LLM test",
)


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def test_base() -> Path:
    """
    Creates a clean test candidate directory at the start of the session
    and removes it at the end. All tests share this one candidate.
    """
    base = DATA_DIR / TEST_CANDIDATE_ID
    # Clean slate
    if base.exists():
        shutil.rmtree(base)

    for sub in ["cvs", "interviews", "job_screenings/details", "applications"]:
        (base / sub).mkdir(parents=True, exist_ok=True)

    # Seed tracker
    tracker = {
        "candidate_id": TEST_CANDIDATE_ID,
        "name": TEST_CANDIDATE_NAME,
        "stage": "cvs_ingested",
        "profile_completeness": 0,
        "known_gaps": [],
        "last_updated": date.today().isoformat(),
        "interview_sessions": [],
        "job_screenings": [],
        "applications": [],
        "question_bank_version": "1.0",
    }
    (base / "tracker.json").write_text(json.dumps(tracker, indent=2))

    yield base

    # Teardown — remove test candidate
    shutil.rmtree(base, ignore_errors=True)

    # Remove from global index
    index_path = DATA_DIR / "index.json"
    if index_path.exists():
        try:
            index = json.loads(index_path.read_text())
            index.get("candidates", {}).pop(TEST_CANDIDATE_ID, None)
            index_path.write_text(json.dumps(index, indent=2))
        except Exception:
            pass


@pytest.fixture(scope="session")
def sample_profile() -> dict:
    """Minimal realistic profile for Alex Müller."""
    return {
        "name": TEST_CANDIDATE_NAME,
        "email": "alex.mueller@example.com",
        "phone": "+49 30 555 01234",
        "location": "Berlin, Germany",
        "summary": (
            "Product manager with 5 years of experience building financial and "
            "e-commerce products. Based in Berlin, targeting Head of Product roles."
        ),
        "skills": [
            "Product Management", "Agile", "Scrum", "User Research", "A/B Testing",
            "SQL", "Figma", "JIRA", "Stakeholder Management", "API Products",
            "FinTech", "Open Banking", "PSD2", "Roadmap Planning", "Data Analysis",
        ],
        "experience": [
            {
                "title": "Senior Product Manager",
                "company": "Finleap Connect",
                "location": "Berlin",
                "start_date": "Jan 2022",
                "end_date": None,
                "current": True,
                "description": (
                    "Led product strategy for open banking API platform. "
                    "Launched PSD2 features across Germany, Austria, and Spain."
                ),
            },
            {
                "title": "Product Manager",
                "company": "SumUp",
                "location": "Berlin",
                "start_date": "Mar 2019",
                "end_date": "Dec 2021",
                "current": False,
                "description": (
                    "Owned merchant onboarding flow end-to-end. "
                    "Ran A/B tests to improve conversion funnel."
                ),
            },
        ],
        "education": [
            {
                "degree": "M.Sc.",
                "field": "Information Systems",
                "institution": "Humboldt University Berlin",
                "graduation_year": "2017",
            }
        ],
        "languages": [
            {"language": "English", "level": "fluent"},
            {"language": "German", "level": "fluent"},
            {"language": "Mandarin", "level": "native"},
        ],
        "certifications": ["Pragmatic Institute PM Certification, 2020"],
        "preferences": {
            "job_titles": ["Head of Product", "VP of Product"],
            "locations": ["Berlin", "Remote"],
            "remote": "hybrid",
            "salary_min": 100000,
            "industries": ["FinTech", "SaaS"],
        },
        "cv_sources": ["pm_cv.txt"],
        "parsed_date": date.today().isoformat(),
    }


@pytest.fixture(scope="session")
def sample_wishlist() -> dict:
    return {
        "dream_jobs": ["Head of Product", "VP of Product"],
        "also_open_to": ["Senior Product Manager", "Director of Product"],
        "target_industries": ["FinTech", "SaaS", "E-commerce"],
        "avoid_industries": ["Gambling"],
        "target_locations": ["Berlin", "Remote"],
        "remote_preference": "hybrid",
        "willing_to_relocate": "no",
        "company_size": ["scaleup", "enterprise"],
        "target_companies": ["N26", "Revolut", "Personio"],
        "salary_currency": "EUR",
        "salary_min": 100000,
        "salary_target": 130000,
        "must_haves": ["equity", "English-speaking team"],
        "deal_breakers": ["no remote at all"],
        "notes": "",
        "last_updated": date.today().isoformat(),
    }


@pytest.fixture(scope="session")
def n26_job() -> dict:
    job_path = FIXTURES_DIR / "jobs" / "head_of_product_n26.json"
    return json.loads(job_path.read_text())
