"""Integration tests for gap analysis — requires GOOGLE_API_KEY."""

import json

import pytest

from conftest import requires_api
from gap_analysis import extract_gaps_for_job, synthesise_gap_report
from llm_client import LLMClient

REQUIRED_GAP_KEYS = {"category", "description", "raw_question"}
VALID_CATEGORIES = {"metrics", "skills", "experience", "preferences", "soft_skills"}
VALID_PRIORITIES = {"high", "medium", "low"}
REQUIRED_REPORT_KEYS = {"gap_id", "category", "description", "affected_jobs",
                        "question", "priority", "resolved"}


@requires_api
class TestExtractGapsForJob:
    def test_returns_list(self, sample_profile, n26_job):
        client = LLMClient()
        gaps = extract_gaps_for_job(n26_job, sample_profile, client)
        assert isinstance(gaps, list)

    def test_gaps_have_required_keys(self, sample_profile, n26_job):
        client = LLMClient()
        gaps = extract_gaps_for_job(n26_job, sample_profile, client)
        for gap in gaps:
            missing = REQUIRED_GAP_KEYS - gap.keys()
            assert not missing, f"Gap missing keys: {missing}"

    def test_gaps_have_valid_categories(self, sample_profile, n26_job):
        client = LLMClient()
        gaps = extract_gaps_for_job(n26_job, sample_profile, client)
        for gap in gaps:
            assert gap["category"] in VALID_CATEGORIES, \
                f"Unexpected category: {gap['category']}"

    def test_finds_real_gaps(self, sample_profile, n26_job):
        """Alex's CV lacks team leadership metrics — N26 requires 2+ years managing PMs."""
        client = LLMClient()
        gaps = extract_gaps_for_job(n26_job, sample_profile, client)
        # Should find at least one gap (N26 requires managing other PMs, Alex has none listed)
        assert len(gaps) > 0, "Expected gaps for a PM without explicit leadership experience"

    def test_questions_are_non_empty(self, sample_profile, n26_job):
        client = LLMClient()
        gaps = extract_gaps_for_job(n26_job, sample_profile, client)
        for gap in gaps:
            assert gap["raw_question"].strip(), "Gap question should not be empty"


@requires_api
class TestSynthesiseGapReport:
    def test_returns_prioritised_list(self, sample_profile, sample_wishlist, n26_job):
        client = LLMClient()
        raw_gaps = extract_gaps_for_job(n26_job, sample_profile, client)
        raw_by_job = [{
            "job_id": "head_of_product_n26",
            "title": n26_job["title"],
            "company": n26_job["company"],
            "gaps": raw_gaps,
        }]
        report = synthesise_gap_report(raw_by_job, sample_profile, sample_wishlist, client)

        assert isinstance(report, list)
        assert len(report) > 0

    def test_report_has_required_keys(self, sample_profile, sample_wishlist, n26_job):
        client = LLMClient()
        raw_gaps = extract_gaps_for_job(n26_job, sample_profile, client)
        raw_by_job = [{"job_id": "head_of_product_n26", "title": n26_job["title"],
                       "company": n26_job["company"], "gaps": raw_gaps}]
        report = synthesise_gap_report(raw_by_job, sample_profile, sample_wishlist, client)

        for item in report:
            missing = REQUIRED_REPORT_KEYS - item.keys()
            assert not missing, f"Report item missing keys: {missing}"

    def test_priorities_are_valid(self, sample_profile, sample_wishlist, n26_job):
        client = LLMClient()
        raw_gaps = extract_gaps_for_job(n26_job, sample_profile, client)
        raw_by_job = [{"job_id": "head_of_product_n26", "title": n26_job["title"],
                       "company": n26_job["company"], "gaps": raw_gaps}]
        report = synthesise_gap_report(raw_by_job, sample_profile, sample_wishlist, client)

        for item in report:
            assert item["priority"] in VALID_PRIORITIES

    def test_resolved_is_false_on_creation(self, sample_profile, sample_wishlist, n26_job):
        client = LLMClient()
        raw_gaps = extract_gaps_for_job(n26_job, sample_profile, client)
        raw_by_job = [{"job_id": "head_of_product_n26", "title": n26_job["title"],
                       "company": n26_job["company"], "gaps": raw_gaps}]
        report = synthesise_gap_report(raw_by_job, sample_profile, sample_wishlist, client)

        for item in report:
            assert item["resolved"] is False
