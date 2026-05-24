"""Unit tests for shared utility functions — no LLM required."""

import pytest


class TestStripFences:
    """Test the strip_fences helper used in multiple scripts."""

    def _strip(self, text):
        from gap_analysis import strip_fences
        return strip_fences(text)

    def test_no_fences(self):
        assert self._strip('{"key": "value"}') == '{"key": "value"}'

    def test_json_fences(self):
        raw = '```json\n{"key": "value"}\n```'
        assert self._strip(raw) == '{"key": "value"}'

    def test_plain_fences(self):
        raw = '```\n{"key": "value"}\n```'
        assert self._strip(raw) == '{"key": "value"}'

    def test_strips_whitespace(self):
        raw = '```json\n  {"key": "value"}  \n```'
        assert self._strip(raw).strip() == '{"key": "value"}'

    def test_multiline_json(self):
        raw = '```json\n[\n  {"a": 1},\n  {"b": 2}\n]\n```'
        result = self._strip(raw)
        import json
        parsed = json.loads(result)
        assert len(parsed) == 2


class TestCandidateStageRank:
    """Stage ordering must be consistent — used by progress bar and update_stage."""

    EXPECTED_ORDER = [
        "cvs_ingested",
        "wishlist_done",
        "jobs_screened",
        "gap_analysis_done",
        "interview_in_progress",
        "interview_done",
        "fit_report_done",
        "applications_generated",
    ]

    def test_each_stage_has_higher_rank_than_previous(self):
        from app import STAGE_RANK
        for i in range(len(self.EXPECTED_ORDER) - 1):
            current = self.EXPECTED_ORDER[i]
            nxt = self.EXPECTED_ORDER[i + 1]
            assert STAGE_RANK[current] < STAGE_RANK[nxt], \
                f"Expected {current} < {nxt} in STAGE_RANK"

    def test_all_stages_present(self):
        from app import STAGE_RANK
        for stage in self.EXPECTED_ORDER:
            assert stage in STAGE_RANK, f"Stage '{stage}' missing from STAGE_RANK"


class TestWishlistParsing:
    """CSV and line-split helpers used in Streamlit wishlist form."""

    def _split_csv(self, s):
        return [x.strip() for x in s.split(",") if x.strip()]

    def _split_lines(self, s):
        return [x.strip() for x in s.splitlines() if x.strip()]

    def test_csv_basic(self):
        assert self._split_csv("Berlin, Munich, Remote") == ["Berlin", "Munich", "Remote"]

    def test_csv_trailing_comma(self):
        assert self._split_csv("Berlin, Munich,") == ["Berlin", "Munich"]

    def test_csv_empty(self):
        assert self._split_csv("") == []

    def test_lines_basic(self):
        assert self._split_lines("equity\nflexible hours") == ["equity", "flexible hours"]

    def test_lines_blank_lines_ignored(self):
        assert self._split_lines("equity\n\nflexible hours\n") == ["equity", "flexible hours"]
