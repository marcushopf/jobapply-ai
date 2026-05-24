"""Integration tests for LinkedIn profile generation — requires GOOGLE_API_KEY."""

import json

import pytest

from conftest import requires_api
from linkedin_profile import (
    generate_headline,
    generate_about,
    generate_skills_section,
    generate_experience_descriptions,
)
from llm_client import LLMClient


@requires_api
class TestHeadline:
    def test_returns_string(self, sample_profile, sample_wishlist):
        client = LLMClient()
        headline = generate_headline(sample_profile, sample_wishlist, client)
        assert isinstance(headline, str)
        assert len(headline.strip()) > 0

    def test_within_linkedin_limit(self, sample_profile, sample_wishlist):
        """LinkedIn headline max is 220 chars, but best practice is ≤120."""
        client = LLMClient()
        headline = generate_headline(sample_profile, sample_wishlist, client)
        assert len(headline) <= 220, f"Headline too long: {len(headline)} chars"

    def test_does_not_start_with_i_am(self, sample_profile, sample_wishlist):
        client = LLMClient()
        headline = generate_headline(sample_profile, sample_wishlist, client)
        assert not headline.lower().startswith("i am"), \
            "Headline should not start with 'I am'"


@requires_api
class TestAbout:
    def test_returns_string(self, sample_profile, sample_wishlist):
        client = LLMClient()
        about = generate_about(sample_profile, sample_wishlist, {}, client)
        assert isinstance(about, str)
        assert len(about.strip()) > 0

    def test_word_count_in_range(self, sample_profile, sample_wishlist):
        """About should be 250–400 words."""
        client = LLMClient()
        about = generate_about(sample_profile, sample_wishlist, {}, client)
        words = len(about.split())
        assert 150 <= words <= 500, f"About word count {words} out of range"

    def test_written_in_first_person(self, sample_profile, sample_wishlist):
        client = LLMClient()
        about = generate_about(sample_profile, sample_wishlist, {}, client)
        assert any(word in about.lower() for word in [" i ", " i've", " my ", " i'm"]), \
            "About should be written in first person"


@requires_api
class TestSkills:
    def test_returns_list(self, sample_profile, sample_wishlist):
        client = LLMClient()
        skills = generate_skills_section(sample_profile, sample_wishlist, {}, client)
        assert isinstance(skills, list)

    def test_returns_50_skills(self, sample_profile, sample_wishlist):
        client = LLMClient()
        skills = generate_skills_section(sample_profile, sample_wishlist, {}, client)
        assert len(skills) == 50, f"Expected 50 skills, got {len(skills)}"

    def test_all_strings(self, sample_profile, sample_wishlist):
        client = LLMClient()
        skills = generate_skills_section(sample_profile, sample_wishlist, {}, client)
        for skill in skills:
            assert isinstance(skill, str) and skill.strip(), \
                f"Non-string or empty skill: {skill!r}"

    def test_no_duplicates(self, sample_profile, sample_wishlist):
        client = LLMClient()
        skills = generate_skills_section(sample_profile, sample_wishlist, {}, client)
        lower = [s.lower() for s in skills]
        assert len(lower) == len(set(lower)), "Duplicate skills found"


@requires_api
class TestExperienceDescriptions:
    def test_returns_list(self, sample_profile, sample_wishlist):
        client = LLMClient()
        result = generate_experience_descriptions(sample_profile, sample_wishlist, client)
        assert isinstance(result, list)

    def test_matches_experience_count(self, sample_profile, sample_wishlist):
        client = LLMClient()
        result = generate_experience_descriptions(sample_profile, sample_wishlist, client)
        expected = len(sample_profile["experience"])
        assert len(result) == expected, \
            f"Expected {expected} experience entries, got {len(result)}"

    def test_each_entry_has_required_keys(self, sample_profile, sample_wishlist):
        client = LLMClient()
        result = generate_experience_descriptions(sample_profile, sample_wishlist, client)
        for entry in result:
            assert "title" in entry
            assert "company" in entry
            assert "description" in entry
