#!/usr/bin/env python3
"""
Stage 1b: Wishlist Setup

Interactive CLI to capture what the candidate actually wants — dream jobs,
target industries, locations, salary, must-haves, and deal-breakers.
This drives job search queries and the fit report.

Usage:
    python scripts/setup_wishlist.py --candidate marcus_hopf
    python scripts/setup_wishlist.py --candidate marcus_hopf --edit   # re-open existing wishlist
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import date


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def candidate_dir(candidate_id: str) -> Path:
    d = Path("candidates") / candidate_id
    if not d.exists():
        sys.exit(f"Candidate not found: {candidate_id}\nRun ingest_cvs.py first.")
    return d


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value if value else default


def ask_list(prompt: str, example: str = "") -> list[str]:
    hint = f" (comma-separated, e.g. {example})" if example else " (comma-separated)"
    raw = input(f"{prompt}{hint}: ").strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def ask_choice(prompt: str, options: list[str], default: str = "") -> str:
    opts = "/".join(options)
    suffix = f" [{default}]" if default else ""
    while True:
        value = input(f"{prompt} ({opts}){suffix}: ").strip().lower()
        if not value and default:
            return default
        if value in [o.lower() for o in options]:
            return value
        print(f"  Please choose one of: {opts}")


def ask_int(prompt: str, default: int = None) -> int | None:
    suffix = f" [{default}]" if default is not None else " (leave blank to skip)"
    raw = input(f"{prompt}{suffix}: ").strip()
    if not raw:
        return default
    try:
        return int(raw.replace(",", "").replace(".", ""))
    except ValueError:
        print("  Please enter a number.")
        return ask_int(prompt, default)


# ---------------------------------------------------------------------------
# Interview
# ---------------------------------------------------------------------------

def run_wishlist_interview(existing: dict = None) -> dict:
    e = existing or {}

    print("\n" + "="*60)
    print("  WISHLIST SETUP")
    print("  Tell us what you're looking for. Press Enter to skip.")
    print("="*60 + "\n")

    print("--- Target Roles ---")
    dream_jobs = ask_list(
        "What are your dream job titles",
        "Head of Product, Senior PM, Product Director",
    ) or e.get("dream_jobs", [])

    also_open_to = ask_list(
        "Also open to (other titles you'd consider)",
        "Product Manager, Strategy Lead",
    ) or e.get("also_open_to", [])

    print("\n--- Industries ---")
    target_industries = ask_list(
        "Which industries do you want to work in",
        "FinTech, HealthTech, SaaS, E-commerce",
    ) or e.get("target_industries", [])

    avoid_industries = ask_list(
        "Industries you want to avoid",
        "Gambling, Tobacco",
    ) or e.get("avoid_industries", [])

    print("\n--- Location ---")
    target_locations = ask_list(
        "Preferred locations",
        "Berlin, Munich, Vienna, Remote",
    ) or e.get("target_locations", [])

    remote_pref = ask_choice(
        "Remote preference",
        ["remote", "hybrid", "onsite", "flexible"],
        default=e.get("remote_preference", "flexible"),
    )

    willing_to_relocate = ask_choice(
        "Willing to relocate",
        ["yes", "no", "maybe"],
        default=e.get("willing_to_relocate", "maybe"),
    )

    print("\n--- Company ---")
    company_size = ask_list(
        "Preferred company size",
        "startup, scaleup, enterprise",
    ) or e.get("company_size", [])

    target_companies = ask_list(
        "Specific companies you'd love to work at",
        "Stripe, N26, Zalando, Revolut",
    ) or e.get("target_companies", [])

    print("\n--- Salary ---")
    currency = ask("Currency", default=e.get("salary_currency", "EUR"))
    salary_min = ask_int("Minimum salary (gross/year)", default=e.get("salary_min"))
    salary_target = ask_int("Target salary (gross/year)", default=e.get("salary_target"))

    print("\n--- Deal-makers & Deal-breakers ---")
    must_haves = ask_list(
        "Must-haves (things you won't compromise on)",
        "equity, English-speaking team, flexible hours",
    ) or e.get("must_haves", [])

    deal_breakers = ask_list(
        "Deal-breakers (things that rule out a job)",
        "no remote at all, no growth path, bureaucratic culture",
    ) or e.get("deal_breakers", [])

    print("\n--- Anything else? ---")
    notes = ask("Free text — anything else we should know", default=e.get("notes", ""))

    wishlist = {
        "dream_jobs": dream_jobs,
        "also_open_to": also_open_to,
        "target_industries": target_industries,
        "avoid_industries": avoid_industries,
        "target_locations": target_locations,
        "remote_preference": remote_pref,
        "willing_to_relocate": willing_to_relocate,
        "company_size": company_size,
        "target_companies": target_companies,
        "salary_currency": currency,
        "salary_min": salary_min,
        "salary_target": salary_target,
        "must_haves": must_haves,
        "deal_breakers": deal_breakers,
        "notes": notes,
        "last_updated": date.today().isoformat(),
    }

    return wishlist


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Set up candidate wishlist")
    parser.add_argument("--candidate", required=True, help="Candidate ID (e.g. marcus_hopf)")
    parser.add_argument("--edit", action="store_true", help="Edit existing wishlist")
    args = parser.parse_args()

    base = candidate_dir(args.candidate)
    wishlist_path = base / "wishlist.json"

    existing = None
    if wishlist_path.exists():
        existing = json.loads(wishlist_path.read_text())
        if not args.edit:
            print(f"Wishlist already exists for {args.candidate}.")
            print("Use --edit to modify it, or view it at:")
            print(f"  {wishlist_path}")
            print("\nCurrent wishlist:")
            print(json.dumps(existing, indent=2))
            return

    wishlist = run_wishlist_interview(existing)

    wishlist_path.write_text(json.dumps(wishlist, indent=2))
    print(f"\nWishlist saved to {wishlist_path}")

    # Show search queries that will be used
    all_titles = wishlist["dream_jobs"] + wishlist["also_open_to"]
    locations = wishlist["target_locations"]
    print("\nJob search queries that will be used:")
    for title in all_titles[:3]:
        for loc in locations[:2]:
            print(f"  '{title} {loc}'")

    print(f"\nNext step: screen jobs")
    print(f"  python scripts/screen_jobs.py --candidate {args.candidate}")


if __name__ == "__main__":
    main()
