"""Integration tests for application generation — requires GOOGLE_API_KEY."""

import pytest

from helpers import requires_api, CachedLLMClient
from generate_application import generate_cover_letter, generate_tailored_cv

pytestmark = requires_api


@pytest.fixture(scope="module")
def llm_client():
    return CachedLLMClient()


@pytest.fixture(scope="module")
def cover_letter(llm_client, sample_profile, n26_job):
    return generate_cover_letter(n26_job, sample_profile, llm_client)


@pytest.fixture(scope="module")
def tailored_cv(llm_client, sample_profile, n26_job):
    return generate_tailored_cv(n26_job, sample_profile, llm_client)


class TestCoverLetter:
    def test_returns_non_empty_string(self, cover_letter):
        assert isinstance(cover_letter, str)
        assert len(cover_letter.strip()) > 0

    def test_word_count_in_range(self, cover_letter):
        """Cover letter should be 300–500 words."""
        word_count = len(cover_letter.split())
        assert 200 <= word_count <= 600, \
            f"Cover letter word count {word_count} outside expected range 200–600"

    def test_contains_candidate_name(self, cover_letter):
        assert "Alex" in cover_letter or "Muller" in cover_letter, \
            "Cover letter should reference the candidate"

    def test_contains_company_name(self, cover_letter):
        assert "N26" in cover_letter, "Cover letter should mention the target company"

    def test_no_unfilled_placeholders(self, cover_letter):
        assert "[Company]" not in cover_letter
        assert "[Name]" not in cover_letter
        assert "[Date]" not in cover_letter
        assert "[Your" not in cover_letter


class TestTailoredCV:
    def test_returns_non_empty_string(self, tailored_cv):
        assert isinstance(tailored_cv, str)
        assert len(tailored_cv.strip()) > 0

    def test_contains_candidate_name(self, tailored_cv):
        assert "Alex" in tailored_cv or "Muller" in tailored_cv

    def test_has_experience_section(self, tailored_cv):
        lower = tailored_cv.lower()
        assert "experience" in lower or "finleap" in lower or "sumup" in lower

    def test_no_unfilled_placeholders(self, tailored_cv):
        assert "[Company]" not in tailored_cv
        assert "[Date]" not in tailored_cv
        assert "TODO" not in tailored_cv
