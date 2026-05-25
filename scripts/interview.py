#!/usr/bin/env python3
"""
Stage 4: Targeted Interview Bot

Reads gap_report.json and asks the candidate targeted questions to fill
unresolved gaps. Saves answers into profile.json and marks each gap resolved.

Usage:
    python scripts/interview.py --candidate marcus_hopf
    python scripts/interview.py --candidate marcus_hopf --priority high
"""

import argparse
import json
import re
import signal
import sys
from datetime import date, datetime
from pathlib import Path

import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).parent))

from llm_client import LLMClient
from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path: Path) -> dict:
    if not path.exists():
        sys.exit(f"File not found: {path}")
    return json.loads(path.read_text())


def save_json(path: Path, data: dict):
    path.write_text(json.dumps(data, indent=2))


def candidate_dir(candidate_id: str) -> Path:
    d = Path("data/candidates") / candidate_id
    if not d.exists():
        sys.exit(f"Candidate not found: {candidate_id}\nRun ingest_cvs.py first.")
    return d


def next_session_number(interviews_dir: Path) -> int:
    nums = []
    for f in interviews_dir.glob("session_*.md"):
        m = re.search(r"session_(\d+)", f.name)
        if m:
            nums.append(int(m.group(1)))
    return max(nums) + 1 if nums else 1


def strip_fences(text: str) -> str:
    text = re.sub(r"^```[a-z]*\n?", "", text.strip())
    text = re.sub(r"\n?```$", "", text).strip()
    for start, end in [("[", "]"), ("{", "}")]:
        s, e = text.find(start), text.rfind(end)
        if s != -1 and e > s:
            return text[s:e + 1]
    return text


# ---------------------------------------------------------------------------
# Claude: extract structured info from an answer
# ---------------------------------------------------------------------------

def extract_profile_update(gap: dict, answer: str, profile: dict,
                            client: LLMClient) -> dict:
    prompt = f"""You are enriching a job candidate's profile from an interview answer.

Gap:
  Category: {gap['category']}
  Description: {gap['description']}
  Question asked: {gap['question']}

Candidate's answer:
{answer}

Profile context (summary + experience snippet):
{json.dumps({k: profile.get(k) for k in ['summary', 'skills']}, indent=2)[:1500]}

Extract the key information from this answer. Return ONLY valid JSON:
{{
  "extracted_summary": "One sentence summarising what was learned",
  "evidence": "Specific facts, metrics, or examples from the answer (verbatim where possible)"
}}"""

    raw = strip_fences(client.chat(prompt, max_tokens=512))
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Apply enrichment to profile
# ---------------------------------------------------------------------------

def apply_enrichment(profile: dict, gap: dict, answer: str, enrichment: dict):
    if "interview_additions" not in profile:
        profile["interview_additions"] = []

    profile["interview_additions"].append({
        "gap_id": gap["gap_id"],
        "category": gap["category"],
        "question": gap["question"],
        "answer": answer,
        "extracted_summary": enrichment.get("extracted_summary", ""),
        "evidence": enrichment.get("evidence", ""),
        "added_date": date.today().isoformat(),
    })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Run targeted interview for a candidate")
    parser.add_argument("--candidate", required=True, help="Candidate ID (e.g. marcus_hopf)")
    parser.add_argument(
        "--priority",
        choices=["high", "medium", "low", "all"],
        default="all",
        help="Only cover gaps at or above this priority level (default: all)",
    )
    args = parser.parse_args()

    candidate_id = args.candidate
    base = candidate_dir(candidate_id)

    profile = load_json(base / "profile.json")
    gap_report = load_json(base / "gap_report.json")

    priority_rank = {"high": 0, "medium": 1, "low": 2}
    max_rank = {"high": 0, "medium": 1, "low": 2, "all": 2}[args.priority]

    pending = [
        g for g in gap_report["gaps"]
        if not g.get("resolved") and priority_rank.get(g["priority"], 99) <= max_rank
    ]
    pending.sort(key=lambda g: priority_rank.get(g["priority"], 99))

    if not pending:
        print(f"No unresolved gaps for {candidate_id} at priority '{args.priority}'.")
        print("Run fit_report.py or generate_application.py for the next step.")
        return

    interviews_dir = base / "interviews"
    interviews_dir.mkdir(exist_ok=True)
    session_num = next_session_number(interviews_dir)

    client = LLMClient()

    transcript = [
        f"# Interview Session {session_num:03d}",
        f"**Candidate:** {profile.get('name', candidate_id)}",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Questions:** {len(pending)} (priority filter: {args.priority})",
        "",
        "---",
        "",
    ]

    print(f"\n{'='*60}")
    print(f"  TARGETED INTERVIEW — {profile.get('name', candidate_id).upper()}")
    print(f"{'='*60}")
    print(f"  {len(pending)} question(s) to cover")
    print(f"  Ordered: high → medium → low priority")
    print(f"  Type 'skip' to skip a question")
    print(f"  Ctrl+C at any time to save and exit")
    print(f"{'='*60}\n")

    answered = 0
    skipped = 0
    interrupted = False

    def handle_interrupt(sig, frame):
        nonlocal interrupted
        interrupted = True
        print("\n\n[Saving progress and exiting...]")

    signal.signal(signal.SIGINT, handle_interrupt)

    for i, gap in enumerate(pending, 1):
        if interrupted:
            break

        badge = {"high": "[HIGH]", "medium": "[MED] ", "low": "[LOW] "}.get(gap["priority"], "      ")
        print(f"Question {i}/{len(pending)} {badge} {gap['gap_id']}")
        print(f"  {gap['question']}\n")

        transcript += [
            f"## Q{i} — {gap['gap_id']} ({gap['priority']})",
            f"**{gap['question']}**",
            "",
        ]

        print("  Your answer (press Enter twice to submit, or type 'skip'):")
        lines = []
        try:
            while not interrupted:
                line = input("  > ")
                if line.strip().lower() == "skip":
                    lines = []
                    break
                if line == "" and lines:
                    break
                if line == "":
                    continue
                lines.append(line)
        except EOFError:
            pass

        answer = "\n".join(lines).strip()

        if not answer or interrupted:
            skipped += 1
            transcript += ["_(skipped)_", ""]
            print("  [skipped]\n")
            if interrupted:
                break
            continue

        print("\n  [Processing...]\n")

        enrichment = extract_profile_update(gap, answer, profile, client)
        apply_enrichment(profile, gap, answer, enrichment)

        for g in gap_report["gaps"]:
            if g["gap_id"] == gap["gap_id"]:
                g["resolved"] = True
                break

        # Save after every answer so a partial session persists
        save_json(base / "profile.json", profile)
        save_json(base / "gap_report.json", gap_report)

        answered += 1
        transcript += [
            f"> {answer}",
            "",
            f"*Extracted: {enrichment.get('extracted_summary', '')}*",
            "",
        ]
        print(f"  Noted: {enrichment.get('extracted_summary', 'saved.')}\n")

    # Save session transcript
    session_path = interviews_dir / f"session_{session_num:03d}.md"
    transcript += [
        "---",
        f"*Session {session_num:03d} — {answered} answered, {skipped} skipped*",
    ]
    session_path.write_text("\n".join(transcript))

    # Update tracker
    tracker_path = base / "tracker.json"
    tracker = json.loads(tracker_path.read_text()) if tracker_path.exists() else {}
    remaining = sum(1 for g in gap_report["gaps"] if not g.get("resolved"))
    tracker["stage"] = "interview_in_progress" if (interrupted or remaining > 0) else "interview_done"
    tracker.setdefault("interviews", []).append({
        "session": session_num,
        "date": date.today().isoformat(),
        "answered": answered,
        "skipped": skipped,
        "remaining_gaps": remaining,
    })
    tracker["last_updated"] = date.today().isoformat()
    save_json(tracker_path, tracker)

    print(f"{'='*60}")
    print(f"  SESSION {session_num:03d} COMPLETE")
    print(f"{'='*60}")
    print(f"  Answered:  {answered}")
    print(f"  Skipped:   {skipped}")
    print(f"  Remaining: {remaining} unresolved gap(s)")
    print(f"  Transcript: {session_path}")

    if remaining == 0:
        print(f"\n  All gaps resolved — ready for Stage 5.")
        print(f"  python scripts/fit_report.py --candidate {candidate_id}")
        print(f"  python scripts/generate_application.py --candidate {candidate_id}")
    else:
        print(f"\n  Run again to cover remaining gaps:")
        print(f"  python scripts/interview.py --candidate {candidate_id}")

    print(f"{'='*60}")


if __name__ == "__main__":
    main()
