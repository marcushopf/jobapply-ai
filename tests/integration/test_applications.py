"""Integration tests for application generation — requires GOOGLE_API_KEY."""

import pytest

from conftest import requires_api
from generate_application import generate_cover_letter, generate_tailored_cv
from llm_client import LLMClient


@requires_api
class TestCoverLetter:
    def test_returns_non_empty_string(self, sample_profile, n26_job):
        client = LLMClient()
        cl = generate_cover_letter(n26_job, sample_profile, client)
        assert isinstance(cl, str)
        assert len(cl.strip()) > 0

    def test_word_count_in_range(self, sample_profile, n26_job):
        """Cover letter should be 300–500 words."""
        client = LLMClient()
        cl = generate_cover_letter(n26_job, sample_profile, client)
        word_count = len(cl.split())
        assert 200 <= word_count <= 600, \
            f"Cover letter word count {word_count} outside expected range 200–600"

    def test_contains_candidate_name(self, sample_profile, n26_job):
        client = LLMClient()
        cl = generate_cover_letter(n26_job, sample_profile, client)
        assert "Alex" in cl or "Muller" in cl, \
            "Cover letter should reference the candidate"

    def test_contains_company_name(self, sample_profile, n26_job):
        client = LLMClient()
        cl = generate_cover_letter(n26_job, sample_profile, client)
        assert "N26" in cl, "Cover letter should mention the target company"

    def test_no_unfilled_placeholders(self, sample_profile, n26_job):
        """LLM must not leave template placeholders like [Company] or [Date]."""
        client = LLMClient()
        cl = generate_cover_letter(n26_job, sample_profile, client)
        assert "[Company]" not in cl
        assert "[Name]" not in cl
        assert "[Date]" not in cl
        assert "[Your" not in cl


@requires_api
class TestTailoredCV:
    def test_returns_non_empty_string(self, sample_profile, n26_job):
        client = LLMClient()
        cv = generate_tailored_cv(n26_job, sample_profile, client)
        assert isinstance(cv, str)
        assert len(cv.strip()) > 0

    def test_contains_candidate_name(self, sample_profile, n26_job):
        client = LLMClient()
        cv = generate_tailored_cv(n26_job, sample_profile, client)
        assert "Alex" in cv or "Muller" in cv

    def test_has_experience_section(self, sample_profile, n26_job):
        client = LLMClient()
        cv = generate_tailored_cv(n26_job, sample_profile, client)
        lower = cv.lower()
        assert "experience" in lower or "finleap" in lower or "sumup" in lower

    def test_no_unfilled_placeholders(self, sample_profile, n26_job):
        client = LLMClient()
        cv = generate_tailored_cv(n26_job, sample_profile, client)
        assert "[Company]" not in cv
        assert "[Date]" not in cv
        assert "TODO" not in cv
