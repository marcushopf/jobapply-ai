"""Unit tests for CV ingestion helpers — no LLM required."""

from pathlib import Path

import pytest

from ingest_cvs import candidate_id_from_name, extract_text

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestCandidateIdFromName:
    def test_basic_name(self):
        assert candidate_id_from_name("Jane Doe") == "jane_doe"

    def test_name_with_title(self):
        assert candidate_id_from_name("Dr. Alex Müller") == "dr_alex_muller"

    def test_extra_spaces(self):
        assert candidate_id_from_name("  Anna  Müller  ") == "anna_m_ller"

    def test_hyphenated_name(self):
        assert candidate_id_from_name("Anna-Lena Koch") == "anna_lena_koch"

    def test_single_word(self):
        assert candidate_id_from_name("Madonna") == "madonna"

    def test_all_uppercase(self):
        assert candidate_id_from_name("JOHN DOE") == "john_doe"


class TestExtractText:
    def test_txt_file(self):
        cv_path = FIXTURES_DIR / "cvs" / "pm_cv.txt"
        text = extract_text(cv_path)
        assert "alex muller" in text.lower()
        assert "product manager" in text.lower()
        assert len(text) > 200

    def test_txt_file_not_empty(self):
        cv_path = FIXTURES_DIR / "cvs" / "pm_cv.txt"
        text = extract_text(cv_path)
        assert text.strip() != ""

    def test_unsupported_extension_exits(self, tmp_path):
        bad_file = tmp_path / "test.xyz"
        bad_file.write_text("content")
        with pytest.raises(SystemExit):
            extract_text(bad_file)
