"""
Scans all git-tracked files for PII patterns.

Catches specific strings that were previously removed from this repo, plus
generic patterns (real email addresses, real filesystem paths). Run as part
of the normal unit test suite — no LLM required.
"""

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parents[3]
THIS_FILE = Path(__file__).relative_to(REPO_ROOT)

# Specific strings that must never reappear — exact PII removed from this repo.
# This file is excluded from its own scan, so these literals are safe here.
BANNED_STRINGS = [
    "Sarah Chen",
    "sarah.chen@email.com",
    "+49 151 234 56789",
    "sarahchen-pm",
    "test_sarah_chen",
    "dr_sarah_chen",
    "Marcus Hopf",
    "/Users/marcus/Google Drive",
]

# File extensions that cannot be read as UTF-8 text — skip them.
BINARY_EXTENSIONS = {".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pyc"}

# Email domains that are intentionally synthetic — never flag these.
SAFE_EMAIL_DOMAINS = {"example.com", "example.org", "example.net"}

# Known-safe email substrings (CI bots, GitHub noreply, etc.)
SAFE_EMAIL_SUBSTRINGS = {"noreply", "github.com", "anthropic.com"}

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})")

# Flags real /Users/<name>/ paths — placeholder like /path/to/... won't match.
PATH_RE = re.compile(r"/Users/[a-zA-Z][a-zA-Z0-9_.-]+/")


def tracked_text_files():
    result = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, cwd=REPO_ROOT
    )
    for rel in result.stdout.splitlines():
        path = REPO_ROOT / rel.strip()
        if path.suffix.lower() in BINARY_EXTENSIONS:
            continue
        if Path(rel.strip()) == THIS_FILE:
            continue  # don't scan ourselves — we contain the banned strings as literals
        yield path, Path(rel.strip())


class TestNoPII:
    def test_no_banned_strings(self):
        violations = []
        for path, rel in tracked_text_files():
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for banned in BANNED_STRINGS:
                if banned.lower() in text.lower():
                    for i, line in enumerate(text.splitlines(), 1):
                        if banned.lower() in line.lower():
                            violations.append(f"{rel}:{i}  →  found '{banned}'")
        assert not violations, (
            "PII detected in tracked files:\n" + "\n".join(violations)
        )

    def test_no_real_email_addresses(self):
        violations = []
        for path, rel in tracked_text_files():
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                for match in EMAIL_RE.finditer(line):
                    domain = match.group(1).lower()
                    email = match.group(0).lower()
                    if domain in SAFE_EMAIL_DOMAINS:
                        continue
                    if any(s in email for s in SAFE_EMAIL_SUBSTRINGS):
                        continue
                    violations.append(f"{rel}:{i}  →  real email '{match.group(0)}'")
        assert not violations, (
            "Real email addresses found in tracked files:\n" + "\n".join(violations)
        )

    def test_no_real_filesystem_paths(self):
        violations = []
        for path, rel in tracked_text_files():
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                for match in PATH_RE.finditer(line):
                    violations.append(
                        f"{rel}:{i}  →  filesystem path '{match.group(0)}'"
                    )
        assert not violations, (
            "Real filesystem paths found in tracked files:\n" + "\n".join(violations)
        )
