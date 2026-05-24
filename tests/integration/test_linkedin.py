"""Integration tests for LinkedIn profile generation — requires GOOGLE_API_KEY."""

import pytest

from helpers import requires_api, CachedLLMClient
from linkedin_profile import (
    generate_headline,
    generate_about,
    generate_skills_section,
    generate_experience_descriptions,
)
pytestmark = requires_api


@pytest.fixture(scope="module")
def llm_client():
    return CachedLLMClient()


@pytest.fixture(scope="module")
def headline(llm_client, sample_profile, sample_wishlist):
    return generate_headline(sample_profile, sample_wishlist, llm_client)


@pytest.fixture(scope="module")
def about(llm_client, sample_profile, sample_wishlist):
    return generate_about(sample_profile, sample_wishlist, {}, llm_client)


@pytest.fixture(scope="module")
def skills(llm_client, sample_profile, sample_wishlist):
    return generate_skills_section(sample_profile, sample_wishlist, {}, llm_client)


@pytest.fixture(scope="module")
def experience_descriptions(llm_client, sample_profile, sample_wishlist):
    return generate_experience_descriptions(sample_profile, sample_wishlist, llm_client)


class TestHeadline:
    def test_returns_string(self, headline):
        assert isinstance(headline, str)
        assert len(headline.strip()) > 0

    def test_within_linkedin_limit(self, headline):
        assert len(headline) <= 220, f"Headline too long: {len(headline)} chars"

    def test_does_not_start_with_i_am(self, headline):
        assert not headline.lower().startswith("i am"), \
            "Headline should not start with 'I am'"


class TestAbout:
    def test_returns_string(self, about):
        assert isinstance(about, str)
        assert len(about.strip()) > 0

    def test_word_count_in_range(self, about):
        words = len(about.split())
        assert 150 <= words <= 500, f"About word count {words} out of range"

    def test_written_in_first_person(self, about):
        assert any(word in about.lower() for word in [" i ", " i've", " my ", " i'm"]), \
            "About should be written in first person"


class TestSkills:
    def test_returns_list(self, skills):
        assert isinstance(skills, list)

    def test_returns_50_skills(self, skills):
        assert len(skills) == 50, f"Expected 50 skills, got {len(skills)}"

    def test_all_strings(self, skills):
        for skill in skills:
            assert isinstance(skill, str) and skill.strip(), \
                f"Non-string or empty skill: {skill!r}"

    def test_no_duplicates(self, skills):
        lower = [s.lower() for s in skills]
        assert len(lower) == len(set(lower)), "Duplicate skills found"


class TestExperienceDescriptions:
    def test_returns_list(self, experience_descriptions):
        assert isinstance(experience_descriptions, list)

    def test_matches_experience_count(self, experience_descriptions, sample_profile):
        expected = len(sample_profile["experience"])
        assert len(experience_descriptions) == expected, \
            f"Expected {expected} experience entries, got {len(experience_descriptions)}"

    def test_each_entry_has_required_keys(self, experience_descriptions):
        for entry in experience_descriptions:
            assert "title" in entry
            assert "company" in entry
            assert "description" in entry
