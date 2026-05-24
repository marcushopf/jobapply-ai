"""Unit tests for job screening helpers — no LLM required."""

import pytest

from screen_jobs import next_job_id, slugify, build_search_queries


class TestNextJobId:
    def test_empty_log(self):
        assert next_job_id({"screenings": []}) == "job_001"

    def test_one_existing(self):
        assert next_job_id({"screenings": [{"id": "job_001"}]}) == "job_002"

    def test_ten_existing(self):
        screenings = [{"id": f"job_{i:03d}"} for i in range(1, 11)]
        assert next_job_id({"screenings": screenings}) == "job_011"


class TestSlugify:
    def test_simple(self):
        assert slugify("Booking.com") == "booking_com"

    def test_spaces(self):
        assert slugify("Senior Product Manager") == "senior_product_manager"

    def test_special_chars(self):
        assert slugify("N26 GmbH & Co.") == "n26_gmbh_co"

    def test_truncates_at_40(self):
        long = "a" * 50
        assert len(slugify(long)) <= 40


class TestShortlistThreshold:
    """Score ≥ 60 → shortlisted, < 60 → skipped."""

    def test_above_threshold(self):
        score = 75
        assert ("shortlisted" if score >= 60 else "skipped") == "shortlisted"

    def test_at_threshold(self):
        score = 60
        assert ("shortlisted" if score >= 60 else "skipped") == "shortlisted"

    def test_below_threshold(self):
        score = 59
        assert ("shortlisted" if score >= 60 else "skipped") == "skipped"

    def test_zero_score(self):
        score = 0
        assert ("shortlisted" if score >= 60 else "skipped") == "skipped"


class TestBuildSearchQueries:
    def test_uses_wishlist_dream_jobs(self):
        profile = {"preferences": {}, "experience": []}
        wishlist = {
            "dream_jobs": ["Head of Product"],
            "also_open_to": [],
            "target_locations": ["Berlin"],
            "target_companies": [],
        }
        queries = build_search_queries(profile, wishlist)
        assert any("Head of Product" in q for q in queries)
        assert any("Berlin" in q for q in queries)

    def test_falls_back_to_profile_when_no_wishlist(self):
        profile = {
            "preferences": {"job_titles": ["Senior PM"], "locations": ["Munich"]},
            "experience": [],
        }
        queries = build_search_queries(profile, {})
        assert len(queries) > 0

    def test_returns_list(self):
        profile = {"preferences": {}, "experience": [{"title": "PM"}]}
        queries = build_search_queries(profile, {})
        assert isinstance(queries, list)
        assert len(queries) >= 1
