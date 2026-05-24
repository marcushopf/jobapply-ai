"""Integration tests for gap analysis — requires GOOGLE_API_KEY."""

import pytest

from helpers import requires_api, CachedLLMClient
from gap_analysis import extract_gaps_for_job, synthesise_gap_report

pytestmark = requires_api

REQUIRED_GAP_KEYS = {"category", "description", "raw_question"}
VALID_CATEGORIES = {"metrics", "skills", "experience", "preferences", "soft_skills"}
VALID_PRIORITIES = {"high", "medium", "low"}
REQUIRED_REPORT_KEYS = {"gap_id", "category", "description", "affected_jobs",
                        "question", "priority", "resolved"}


@pytest.fixture(scope="module")
def llm_client():
    return CachedLLMClient()


@pytest.fixture(scope="module")
def raw_gaps(llm_client, sample_profile, n26_job):
    return extract_gaps_for_job(n26_job, sample_profile, llm_client)


@pytest.fixture(scope="module")
def gap_report(llm_client, raw_gaps, sample_profile, sample_wishlist, n26_job):
    raw_by_job = [{
        "job_id": "head_of_product_n26",
        "title": n26_job["title"],
        "company": n26_job["company"],
        "gaps": raw_gaps,
    }]
    return synthesise_gap_report(raw_by_job, sample_profile, sample_wishlist, llm_client)


class TestExtractGapsForJob:
    def test_returns_list(self, raw_gaps):
        assert isinstance(raw_gaps, list)

    def test_gaps_have_required_keys(self, raw_gaps):
        for gap in raw_gaps:
            missing = REQUIRED_GAP_KEYS - gap.keys()
            assert not missing, f"Gap missing keys: {missing}"

    def test_gaps_have_valid_categories(self, raw_gaps):
        for gap in raw_gaps:
            assert gap["category"] in VALID_CATEGORIES, \
                f"Unexpected category: {gap['category']}"

    def test_finds_real_gaps(self, raw_gaps):
        """Sarah's CV lacks team leadership metrics — N26 requires 2+ years managing PMs."""
        assert len(raw_gaps) > 0, "Expected gaps for a PM without explicit leadership experience"

    def test_questions_are_non_empty(self, raw_gaps):
        for gap in raw_gaps:
            assert gap["raw_question"].strip(), "Gap question should not be empty"


class TestSynthesiseGapReport:
    def test_returns_prioritised_list(self, gap_report):
        assert isinstance(gap_report, list)
        assert len(gap_report) > 0

    def test_report_has_required_keys(self, gap_report):
        for item in gap_report:
            missing = REQUIRED_REPORT_KEYS - item.keys()
            assert not missing, f"Report item missing keys: {missing}"

    def test_priorities_are_valid(self, gap_report):
        for item in gap_report:
            assert item["priority"] in VALID_PRIORITIES

    def test_resolved_is_false_on_creation(self, gap_report):
        for item in gap_report:
            assert item["resolved"] is False
