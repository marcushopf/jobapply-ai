"""
End-to-end pipeline test — requires GOOGLE_API_KEY.

Runs all 6 stages for a test candidate (Sarah Chen) using the N26 job fixture.
Verifies that each stage produces the expected output files and updates the tracker.
"""

import json
from datetime import date
from pathlib import Path

import pytest

from conftest import requires_api, TEST_CANDIDATE_ID, FIXTURES_DIR
from ingest_cvs import parse_profile_with_claude, ensure_structure
from gap_analysis import extract_gaps_for_job, synthesise_gap_report
from interview import extract_profile_update, apply_enrichment
from fit_report import score_job_title, dream_job_deep_analysis
from generate_application import generate_cover_letter, generate_tailored_cv, next_app_number
from format_cv import detect_role_type, reformat_cv, md_to_html
from linkedin_profile import (
    generate_headline, generate_about, generate_skills_section,
    generate_experience_descriptions, generate_open_to_work,
    generate_featured_suggestions, build_profile_doc,
)
from llm_client import LLMClient


@requires_api
class TestFullPipeline:
    """
    Runs stages sequentially. Each test method depends on the previous one
    having written the expected output file to test_base/.
    Uses session-scoped test_base fixture so state carries across methods.
    """

    # ── Stage 1: CV ingestion ──────────────────────────────────────────────

    def test_stage1_profile_extracted(self, test_base, sample_wishlist):
        cv_path = FIXTURES_DIR / "cvs" / "pm_cv.txt"
        text = cv_path.read_text()
        client = LLMClient()

        profile = parse_profile_with_claude([(cv_path.name, text)], "Sarah Chen")
        profile["cv_sources"] = [cv_path.name]

        profile_path = test_base / "profile.json"
        profile_path.write_text(json.dumps(profile, indent=2))

        assert profile_path.exists()
        assert profile.get("name"), "Profile should have a name"
        assert len(profile.get("experience", [])) > 0, "Profile should have experience"
        assert len(profile.get("skills", [])) > 0, "Profile should have skills"

    # ── Stage 1b: Wishlist ─────────────────────────────────────────────────

    def test_stage1b_wishlist_saved(self, test_base, sample_wishlist):
        wishlist_path = test_base / "wishlist.json"
        wishlist_path.write_text(json.dumps(sample_wishlist, indent=2))
        assert wishlist_path.exists()
        loaded = json.loads(wishlist_path.read_text())
        assert loaded["dream_jobs"], "Wishlist should have dream jobs"

    # ── Stage 2: Job screening (manual — no SerpAPI needed) ───────────────

    def test_stage2_job_scored_and_saved(self, test_base, n26_job):
        from screen_jobs import screening_dir, load_screening_log, save_screening_log, next_job_id

        profile = json.loads((test_base / "profile.json").read_text())
        wishlist = json.loads((test_base / "wishlist.json").read_text())
        log = load_screening_log(TEST_CANDIDATE_ID)
        client = LLMClient()

        from screen_jobs import score_job
        score, reasoning = score_job(n26_job, profile, wishlist, client)
        assert 0 <= score <= 100, f"Score {score} out of range"

        job_id = next_job_id(log)
        entry = {
            "id": job_id, **n26_job,
            "date_screened": date.today().isoformat(),
            "match_score": score, "status": "shortlisted", "reasoning": reasoning,
        }
        log["screenings"].append(entry)
        save_screening_log(TEST_CANDIDATE_ID, log)

        d = screening_dir(TEST_CANDIDATE_ID)
        job_file = d / f"{job_id}_n26_head_of_product.json"
        job_file.write_text(json.dumps(entry, indent=2))

        assert job_file.exists()
        assert score > 0

    # ── Stage 3: Gap analysis ──────────────────────────────────────────────

    def test_stage3_gap_report_generated(self, test_base, n26_job):
        profile = json.loads((test_base / "profile.json").read_text())
        wishlist = json.loads((test_base / "wishlist.json").read_text())
        client = LLMClient()

        raw_gaps = extract_gaps_for_job(n26_job, profile, client)
        assert len(raw_gaps) > 0, "Expected gaps for Sarah vs N26 job"

        raw_by_job = [{"job_id": "head_of_product_n26", "title": n26_job["title"],
                       "company": n26_job["company"], "gaps": raw_gaps}]
        gaps = synthesise_gap_report(raw_by_job, profile, wishlist, client)

        counts = {
            "high": sum(1 for g in gaps if g["priority"] == "high"),
            "medium": sum(1 for g in gaps if g["priority"] == "medium"),
            "low": sum(1 for g in gaps if g["priority"] == "low"),
            "total": len(gaps),
        }
        report = {
            "candidate_id": TEST_CANDIDATE_ID,
            "generated_date": date.today().isoformat(),
            "jobs_analyzed": ["head_of_product_n26"],
            "gaps": gaps, "counts": counts,
            "summary": f"{len(gaps)} gaps identified.",
        }
        (test_base / "gap_report.json").write_text(json.dumps(report, indent=2))
        assert (test_base / "gap_report.json").exists()
        assert counts["total"] > 0

    # ── Stage 4: Interview (one answer) ───────────────────────────────────

    def test_stage4_interview_enriches_profile(self, test_base):
        profile = json.loads((test_base / "profile.json").read_text())
        gap_report = json.loads((test_base / "gap_report.json").read_text())
        client = LLMClient()

        pending = [g for g in gap_report["gaps"] if not g.get("resolved")]
        assert pending, "Need at least one unresolved gap to test interview"

        gap = pending[0]
        answer = (
            "At Finleap Connect I managed a team of 3 product managers directly, "
            "running weekly 1-on-1s, quarterly reviews, and career development plans. "
            "I also worked with 2 contract PMs on specific initiatives."
        )

        enrichment = extract_profile_update(gap, answer, profile, client)
        apply_enrichment(profile, gap, answer, enrichment)

        for g in gap_report["gaps"]:
            if g["gap_id"] == gap["gap_id"]:
                g["resolved"] = True
                break

        (test_base / "profile.json").write_text(json.dumps(profile, indent=2))
        (test_base / "gap_report.json").write_text(json.dumps(gap_report, indent=2))

        assert "interview_additions" in profile
        assert len(profile["interview_additions"]) > 0
        assert enrichment.get("extracted_summary"), "Enrichment should have a summary"

    # ── Stage 4b: Fit report ───────────────────────────────────────────────

    def test_stage4b_fit_report_generated(self, test_base):
        profile = json.loads((test_base / "profile.json").read_text())
        wishlist = json.loads((test_base / "wishlist.json").read_text())
        client = LLMClient()

        titles = wishlist.get("dream_jobs", []) + wishlist.get("also_open_to", [])
        assert titles, "Wishlist should have target titles"
        dream_title = titles[0]

        title_fits = []
        for title in titles[:2]:  # limit to 2 for speed
            fit = score_job_title(title, profile, wishlist, client)
            fit["title"] = title
            title_fits.append(fit)

        dream_fit = title_fits[0]
        dream_analysis = dream_job_deep_analysis(dream_title, profile, wishlist, dream_fit, client)

        report = {
            "candidate": profile.get("name"),
            "generated": date.today().isoformat(),
            "dream_job": dream_title,
            "job_title_fits": title_fits,
            "dream_job_analysis": dream_analysis,
        }
        (test_base / "fit_report.json").write_text(json.dumps(report, indent=2))
        assert (test_base / "fit_report.json").exists()
        assert 0 <= dream_fit["fit_score"] <= 100

    # ── Stage 5: Application generation ───────────────────────────────────

    def test_stage5_application_generated(self, test_base, n26_job):
        profile = json.loads((test_base / "profile.json").read_text())
        client = LLMClient()

        apps_dir = test_base / "applications"
        apps_dir.mkdir(exist_ok=True)
        app_num = next_app_number(apps_dir)
        app_dir = apps_dir / f"app_{app_num:03d}_n26_head_of_product"
        app_dir.mkdir(exist_ok=True)

        cover_letter = generate_cover_letter(n26_job, profile, client)
        cv = generate_tailored_cv(n26_job, profile, client)

        (app_dir / "cover_letter.md").write_text(cover_letter)
        (app_dir / "cv_tailored.md").write_text(cv)
        (app_dir / "meta.json").write_text(json.dumps({
            "app_id": app_dir.name, "job_id": "head_of_product_n26",
            "title": n26_job["title"], "company": n26_job["company"],
            "generated_date": date.today().isoformat(), "status": "draft",
        }, indent=2))

        assert (app_dir / "cover_letter.md").exists()
        assert (app_dir / "cv_tailored.md").exists()
        assert "N26" in cover_letter or "n26" in cover_letter.lower()

    # ── Stage 5b: CV formatting ────────────────────────────────────────────

    def test_stage5b_cv_formatted_to_html(self, test_base):
        profile = json.loads((test_base / "profile.json").read_text())
        wishlist = json.loads((test_base / "wishlist.json").read_text())
        client = LLMClient()

        apps_dir = test_base / "applications"
        app_dirs = [d for d in apps_dir.iterdir()
                    if d.is_dir() and (d / "cv_tailored.md").exists()]
        assert app_dirs, "Need at least one application to format"

        app_dir = app_dirs[0]
        meta = json.loads((app_dir / "meta.json").read_text())
        cv_md = (app_dir / "cv_tailored.md").read_text()
        role_type = detect_role_type(meta["title"], wishlist)

        formatted_md = reformat_cv(cv_md, role_type, meta["title"], meta["company"], client)
        html = md_to_html(formatted_md, profile.get("name", ""))

        (app_dir / "cv_formatted.md").write_text(formatted_md)
        (app_dir / "cv_formatted.html").write_text(html)

        assert "<html" in html
        assert "@media print" in html
        assert len(formatted_md) > 100

    # ── Stage 6: LinkedIn profile ──────────────────────────────────────────

    def test_stage6_linkedin_profile_generated(self, test_base):
        profile = json.loads((test_base / "profile.json").read_text())
        wishlist = json.loads((test_base / "wishlist.json").read_text())
        fit_path = test_base / "fit_report.json"
        fit_report = json.loads(fit_path.read_text()) if fit_path.exists() else {}
        client = LLMClient()
        candidate_name = profile.get("name", TEST_CANDIDATE_ID)

        headline = generate_headline(profile, wishlist, client)
        about = generate_about(profile, wishlist, fit_report, client)
        skills = generate_skills_section(profile, wishlist, fit_report, client)
        exp_desc = generate_experience_descriptions(profile, wishlist, client)
        open_to_work = generate_open_to_work(profile, wishlist)
        featured = generate_featured_suggestions(profile, wishlist, client)

        doc = build_profile_doc(headline, about, skills, exp_desc,
                                open_to_work, featured, candidate_name)

        linkedin_path = test_base / "linkedin_profile.md"
        linkedin_path.write_text(doc)

        assert linkedin_path.exists()
        assert len(headline) <= 220
        assert len(skills) == 50
        assert "## Headline" in doc
        assert "## About" in doc
        assert "## Skills" in doc
