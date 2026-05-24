"""Unit tests for CV formatter helpers — no LLM required."""

import pytest

from format_cv import detect_role_type, md_to_html


class TestDetectRoleType:
    # Product roles
    def test_head_of_product(self):
        assert detect_role_type("Head of Product", {}) == "product"

    def test_senior_pm(self):
        assert detect_role_type("Senior Product Manager", {}) == "product"

    def test_vp_product(self):
        assert detect_role_type("VP of Product", {}) == "product"

    # Engineering roles
    def test_software_engineer(self):
        assert detect_role_type("Senior Software Engineer", {}) == "engineering"

    def test_backend_developer(self):
        assert detect_role_type("Backend Developer", {}) == "engineering"

    def test_devops(self):
        assert detect_role_type("DevOps Engineer", {}) == "engineering"

    # Data roles
    def test_data_scientist(self):
        assert detect_role_type("Data Scientist", {}) == "data"

    def test_data_analyst(self):
        assert detect_role_type("Senior Data Analyst", {}) == "data"

    def test_ml_engineer(self):
        assert detect_role_type("ML Engineer", {}) == "data"

    # Management roles
    def test_senior_manager(self):
        assert detect_role_type("Senior Manager Data Science", {}) == "management"

    def test_director(self):
        assert detect_role_type("Director of Engineering", {}) == "management"

    def test_cto(self):
        assert detect_role_type("CTO", {}) == "management"

    # Wishlist fallback
    def test_uses_wishlist_when_title_vague(self):
        wishlist = {"dream_jobs": ["Head of Product"], "also_open_to": []}
        assert detect_role_type("Business Lead", wishlist) == "product"

    # General fallback
    def test_unknown_title(self):
        assert detect_role_type("Business Analyst", {}) == "general"


class TestMdToHtml:
    def test_returns_html_string(self):
        html = md_to_html("# John Doe\n\n## Skills\n\n- Python", "John Doe")
        assert "<html" in html
        assert "<h1>" in html or "John Doe" in html

    def test_contains_candidate_name(self):
        html = md_to_html("# Sarah Chen", "Sarah Chen")
        assert "Sarah Chen" in html

    def test_ats_safe_no_tables(self):
        html = md_to_html("# Test\n\n## Experience", "Test")
        assert "<table" not in html

    def test_has_print_css(self):
        html = md_to_html("# Test", "Test")
        assert "@media print" in html
