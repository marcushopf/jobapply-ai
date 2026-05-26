#!/usr/bin/env python3
"""
JobApply AI — Streamlit web interface
Run: streamlit run app.py
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from dotenv import load_dotenv
load_dotenv()

# ── Constants ──────────────────────────────────────────────────────────────

DATA_DIR = Path("data/candidates")

PAGES = [
    "🏠  Home",
    "1.  Upload CVs",
    "1b. Wishlist",
    "2.  Job Screening",
    "3.  Gap Analysis",
    "4.  Interview",
    "4b. Fit Report",
    "5.  Applications",
    "5b. Format CV",
    "6.  LinkedIn Profile",
]

PROGRESS_STAGES = [
    ("cvs_ingested",            "CVs uploaded"),
    ("wishlist_done",           "Wishlist set"),
    ("jobs_screened",           "Jobs screened"),
    ("gap_analysis_done",       "Gap analysis"),
    ("interview_in_progress",   "Interview started"),
    ("interview_done",          "Interview done"),
    ("fit_report_done",         "Fit report"),
    ("applications_generated",  "Applications"),
]

STAGE_RANK = {s: i for i, (s, _) in enumerate(PROGRESS_STAGES)}

# ── Data helpers ───────────────────────────────────────────────────────────

def load_candidates() -> dict:
    index = DATA_DIR / "index.json"
    if not index.exists():
        return {}
    return json.loads(index.read_text()).get("candidates", {})


def candidate_base(cid: str) -> Path:
    return DATA_DIR / cid


def load_json_file(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def save_json(path: Path, data: dict):
    path.write_text(json.dumps(data, indent=2))


def load_tracker(cid: str) -> dict:
    return load_json_file(candidate_base(cid) / "tracker.json")


def load_profile(cid: str) -> dict:
    return load_json_file(candidate_base(cid) / "profile.json")


def load_gap_report(cid: str) -> dict:
    return load_json_file(candidate_base(cid) / "gap_report.json")


def load_wishlist(cid: str) -> dict:
    return load_json_file(candidate_base(cid) / "wishlist.json")


def update_stage(cid: str, stage: str):
    tracker = load_tracker(cid)
    current_rank = STAGE_RANK.get(tracker.get("stage", ""), -1)
    new_rank = STAGE_RANK.get(stage, -1)
    if new_rank > current_rank:
        tracker["stage"] = stage
    tracker["last_updated"] = date.today().isoformat()
    save_json(candidate_base(cid) / "tracker.json", tracker)


def split_csv(s: str) -> list[str]:
    return [x.strip() for x in s.split(",") if x.strip()]


def split_lines(s: str) -> list[str]:
    return [x.strip() for x in s.splitlines() if x.strip()]


# ── API key helpers ────────────────────────────────────────────────────────

def api_key_exists() -> bool:
    import os
    # Ollama runs locally and needs no API key — skip the Gemini gate entirely.
    if os.getenv("LLM_MODEL", "").strip().startswith("ollama/"):
        return True
    if os.getenv("GOOGLE_API_KEY", "").strip():
        return True
    try:
        import keyring
        return bool(keyring.get_password("jobapply-ai", "google_api_key"))
    except Exception:
        return False


def llm_label() -> str:
    """Friendly name for the active LLM provider, for use in UI messages."""
    import os
    model = os.getenv("LLM_MODEL", "").strip()
    if model.startswith("ollama/"):
        suffix = model.split("/", 1)[1]
        return "local Ollama" if suffix == "auto" else f"Ollama ({suffix})"
    return "Gemini"


# ── Page: API key setup ────────────────────────────────────────────────────

def page_setup():
    st.title("Welcome to JobApply AI")
    st.markdown(
        "Before we start, add your free Google Gemini API key. "
        "It will be saved securely to your system keychain — you won't be asked again."
    )
    st.markdown(
        "Get a free key at **[aistudio.google.com/apikey](https://aistudio.google.com/apikey)**"
    )
    st.divider()

    key = st.text_input("Paste your GOOGLE_API_KEY here", type="password")
    if st.button("Save & Continue", type="primary") and key.strip():
        try:
            import keyring
            keyring.set_password("jobapply-ai", "google_api_key", key.strip())
            st.success("Key saved to your system keychain!")
            st.rerun()
        except Exception as e:
            st.warning(f"Could not save to keychain ({e}). Creating .env file instead.")
            Path(".env").write_text(f"GOOGLE_API_KEY={key.strip()}\n")
            st.success("Key saved to .env file.")
            st.rerun()


# ── Sidebar ────────────────────────────────────────────────────────────────

def render_sidebar() -> tuple[str | None, str]:
    with st.sidebar:
        st.title("JobApply AI")
        st.caption("Smart job application agent")
        st.divider()

        candidates = load_candidates()
        selected_cid = None

        if candidates:
            options = {v["name"]: k for k, v in candidates.items()}
            selected_name = st.selectbox("Candidate", list(options.keys()))
            selected_cid = options[selected_name]

            tracker = load_tracker(selected_cid)
            stage = tracker.get("stage", "")
            current_rank = STAGE_RANK.get(stage, -1)

            st.divider()
            st.caption("Progress")
            for i, (s, label) in enumerate(PROGRESS_STAGES):
                if i < current_rank:
                    st.markdown(f"✅ {label}")
                elif i == current_rank:
                    st.markdown(f"🔄 {label}")
                else:
                    st.markdown(f"⬜ {label}")
        else:
            st.info("No candidates yet — start on the Home page.")

        st.divider()
        page = st.radio("Go to", PAGES, label_visibility="collapsed")

    return selected_cid, page


# ── Page: Home ─────────────────────────────────────────────────────────────

def page_home():
    st.title("JobApply AI")
    st.markdown(
        "Work through the stages in order for each candidate. "
        "Progress is saved automatically."
    )
    st.divider()

    candidates = load_candidates()
    if candidates:
        st.subheader("Existing candidates")
        for cid, meta in candidates.items():
            tracker = load_tracker(cid)
            stage = tracker.get("stage", "not started")
            st.markdown(f"**{meta['name']}** — `{stage}`")
        st.divider()

    st.subheader("Add a new candidate")
    with st.form("new_candidate_form"):
        name = st.text_input("Full name", placeholder="e.g. Maria Müller")
        submitted = st.form_submit_button("Create candidate", type="primary")

    if submitted:
        if not name.strip():
            st.warning("Please enter a name.")
            return
        from ingest_cvs import candidate_id_from_name, ensure_structure, init_tracker, update_candidates_index
        cid = candidate_id_from_name(name)
        ensure_structure(cid)
        tracker_path = candidate_base(cid) / "tracker.json"
        if not tracker_path.exists():
            save_json(tracker_path, init_tracker(cid, name))
        update_candidates_index(cid, name)
        st.success(f"Created: **{name}** (id: `{cid}`). Select them in the sidebar.")
        st.rerun()


# ── Page: Upload CVs ───────────────────────────────────────────────────────

def page_ingest(cid: str):
    st.title("Upload CVs")

    profile = load_profile(cid)
    tracker = load_tracker(cid)

    if profile:
        st.success("Profile already extracted.")
        with st.expander("View current profile"):
            st.json(profile)
        st.markdown("Upload new files below to re-extract and overwrite.")
        st.divider()

    uploaded = st.file_uploader(
        "Upload CV files (PDF, DOCX, or TXT)",
        accept_multiple_files=True,
        type=["pdf", "docx", "txt"],
    )

    if uploaded and st.button("Extract Profile", type="primary"):
        from ingest_cvs import extract_text, parse_profile_with_claude, ensure_structure

        base = ensure_structure(cid)
        cv_texts = []

        with st.spinner("Reading files..."):
            for f in uploaded:
                dest = base / "cvs" / f.name
                dest.write_bytes(f.getbuffer())
                cv_texts.append((f.name, extract_text(dest)))

        with st.spinner(f"Extracting profile with {llm_label()} (this takes ~30s)..."):
            try:
                name = tracker.get("name", cid)
                new_profile = parse_profile_with_claude(cv_texts, name)
                new_profile["cv_sources"] = [f.name for f in uploaded]
                save_json(base / "profile.json", new_profile)
                update_stage(cid, "cvs_ingested")
                st.success("Profile extracted!")
                st.json(new_profile)
            except Exception as e:
                st.error(f"Error extracting profile: {e}")


# ── Page: Wishlist ─────────────────────────────────────────────────────────

def page_wishlist(cid: str):
    st.title("Job Wishlist")
    st.markdown("Tell us what you're looking for. This drives job search and scoring.")

    w = load_wishlist(cid)

    with st.form("wishlist_form"):
        st.subheader("Target roles")
        dream_jobs = st.text_input(
            "Dream job titles (comma-separated)",
            value=", ".join(w.get("dream_jobs", [])),
            placeholder="e.g. Head of Product, VP of Data",
        )
        also_open_to = st.text_input(
            "Also open to",
            value=", ".join(w.get("also_open_to", [])),
            placeholder="e.g. Senior PM, Data Lead",
        )

        st.subheader("Industries")
        col1, col2 = st.columns(2)
        target_industries = col1.text_input(
            "Target industries",
            value=", ".join(w.get("target_industries", [])),
            placeholder="e.g. FinTech, SaaS",
        )
        avoid_industries = col2.text_input(
            "Industries to avoid",
            value=", ".join(w.get("avoid_industries", [])),
            placeholder="e.g. Gambling",
        )

        st.subheader("Location & remote")
        col1, col2, col3 = st.columns(3)
        target_locations = col1.text_input(
            "Preferred locations",
            value=", ".join(w.get("target_locations", [])),
            placeholder="e.g. Berlin, Remote",
        )
        remote_options = ["flexible", "remote", "hybrid", "onsite"]
        remote_pref = col2.selectbox(
            "Remote preference",
            remote_options,
            index=remote_options.index(w.get("remote_preference", "flexible")),
        )
        relocate_options = ["maybe", "yes", "no"]
        willing_to_relocate = col3.selectbox(
            "Willing to relocate",
            relocate_options,
            index=relocate_options.index(w.get("willing_to_relocate", "maybe")),
        )

        st.subheader("Company")
        col1, col2 = st.columns(2)
        company_size = col1.text_input(
            "Preferred company size",
            value=", ".join(w.get("company_size", [])),
            placeholder="e.g. startup, scaleup",
        )
        target_companies = col2.text_input(
            "Target companies",
            value=", ".join(w.get("target_companies", [])),
            placeholder="e.g. Stripe, Zalando",
        )

        st.subheader("Salary")
        col1, col2, col3 = st.columns(3)
        currency = col1.text_input("Currency", value=w.get("salary_currency", "EUR"))
        salary_min = col2.number_input("Min salary (gross/year)", value=w.get("salary_min") or 0, step=5000)
        salary_target = col3.number_input("Target salary", value=w.get("salary_target") or 0, step=5000)

        st.subheader("Must-haves & deal-breakers")
        col1, col2 = st.columns(2)
        must_haves = col1.text_area(
            "Must-haves (one per line)",
            value="\n".join(w.get("must_haves", [])),
            placeholder="e.g. equity\nflexible hours",
        )
        deal_breakers = col2.text_area(
            "Deal-breakers (one per line)",
            value="\n".join(w.get("deal_breakers", [])),
            placeholder="e.g. no remote at all",
        )

        notes = st.text_area("Anything else we should know", value=w.get("notes", ""))

        if st.form_submit_button("Save Wishlist", type="primary"):
            updated = {
                "dream_jobs": split_csv(dream_jobs),
                "also_open_to": split_csv(also_open_to),
                "target_industries": split_csv(target_industries),
                "avoid_industries": split_csv(avoid_industries),
                "target_locations": split_csv(target_locations),
                "remote_preference": remote_pref,
                "willing_to_relocate": willing_to_relocate,
                "company_size": split_csv(company_size),
                "target_companies": split_csv(target_companies),
                "salary_currency": currency,
                "salary_min": int(salary_min) if salary_min else None,
                "salary_target": int(salary_target) if salary_target else None,
                "must_haves": split_lines(must_haves),
                "deal_breakers": split_lines(deal_breakers),
                "notes": notes,
                "last_updated": date.today().isoformat(),
            }
            save_json(candidate_base(cid) / "wishlist.json", updated)
            update_stage(cid, "wishlist_done")
            st.success("Wishlist saved!")
            st.rerun()


# ── Page: Job Screening ────────────────────────────────────────────────────

def page_screening(cid: str):
    st.title("Job Screening")

    details_dir = candidate_base(cid) / "job_screenings" / "details"
    jobs = []
    if details_dir.exists():
        for f in sorted(details_dir.glob("*.json")):
            jobs.append(json.loads(f.read_text()))

    if jobs:
        shortlisted = [j for j in jobs if j.get("status") == "shortlisted"]
        col1, col2, col3 = st.columns(3)
        col1.metric("Total screened", len(jobs))
        col2.metric("Shortlisted", len(shortlisted))
        col3.metric("Skipped", len(jobs) - len(shortlisted))

        if shortlisted:
            st.subheader("Shortlisted jobs")
            for job in shortlisted:
                score = job.get("match_score", "?")
                with st.expander(f"**{job['title']}** @ {job.get('company', '')} — score: {score}/100"):
                    st.write(f"**Reasoning:** {job.get('reasoning', '')}")
                    desc = job.get("description", "")
                    if isinstance(desc, dict):
                        desc = json.dumps(desc, indent=2)
                    if desc:
                        st.text_area("Description", desc, height=150, disabled=True, key=f"desc_{job.get('id')}")
        st.divider()

    st.subheader("Add a job manually")
    st.caption("Paste the job description below — no API key needed for this, the LLM scores it.")

    with st.form("manual_job_form"):
        col1, col2 = st.columns(2)
        title = col1.text_input("Job title *")
        company = col2.text_input("Company *")
        col1, col2 = st.columns(2)
        location = col1.text_input("Location")
        description = st.text_area("Job description *", height=250, placeholder="Paste the full job description here.")
        submitted = st.form_submit_button("Score & Add Job", type="primary")

    if submitted:
        if not title or not company or not description:
            st.warning("Title, company and description are required.")
            return

        from screen_jobs import (
            score_job, screening_dir, load_screening_log,
            save_screening_log, next_job_id, slugify as sc_slug,
        )
        from llm_client import LLMClient

        profile = load_profile(cid)
        wishlist = load_wishlist(cid)
        log = load_screening_log(cid)
        client = LLMClient()

        job = {
            "title": title, "company": company, "location": location,
            "description": description, "source": "manual", "source_url": "",
            "posted": date.today().isoformat(), "employment_type": "",
        }

        with st.spinner(f"Scoring job with {llm_label()}..."):
            try:
                score, reasoning = score_job(job, profile, wishlist, client)
                status = "shortlisted" if score >= 60 else "skipped"
                job_id = next_job_id(log)
                entry = {
                    "id": job_id, **job,
                    "date_screened": date.today().isoformat(),
                    "match_score": score, "status": status, "reasoning": reasoning,
                }
                log["screenings"].append(entry)
                save_screening_log(cid, log)
                d = screening_dir(cid)
                (d / f"{job_id}_{sc_slug(company)}_{sc_slug(title)}.json").write_text(
                    json.dumps(entry, indent=2)
                )
                update_stage(cid, "jobs_screened")
                if status == "shortlisted":
                    st.success(f"Score: **{score}/100** → shortlisted")
                else:
                    st.warning(f"Score: **{score}/100** → skipped (below 60)")
                st.write(f"*{reasoning}*")
                st.rerun()
            except Exception as e:
                st.error(f"Scoring error: {e}")


# ── Page: Gap Analysis ─────────────────────────────────────────────────────

def page_gap_analysis(cid: str):
    st.title("Gap Analysis")

    gap_report = load_gap_report(cid)

    if gap_report.get("gaps"):
        counts = gap_report.get("counts", {})
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total gaps", counts.get("total", 0))
        col2.metric("High", counts.get("high", 0))
        col3.metric("Medium", counts.get("medium", 0))
        col4.metric("Low", counts.get("low", 0))

        st.subheader("Gaps to cover in interview")
        for gap in gap_report["gaps"]:
            resolved = gap.get("resolved", False)
            icon = "✅" if resolved else {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(gap["priority"], "⬜")
            with st.expander(f"{icon} [{gap['gap_id']}] {gap['description']}"):
                st.write(f"**Question:** {gap['question']}")
                st.write(f"**Priority:** `{gap['priority']}`")
                st.write(f"**Affects:** {', '.join(gap.get('affected_jobs', []))}")
        st.divider()

    if st.button("Run Gap Analysis", type="primary"):
        from gap_analysis import extract_gaps_for_job, synthesise_gap_report, load_shortlisted_jobs
        from llm_client import LLMClient

        profile = load_profile(cid)
        wishlist = load_wishlist(cid)

        try:
            jobs = load_shortlisted_jobs(cid)
        except SystemExit as e:
            st.error(str(e))
            return

        client = LLMClient()
        progress = st.progress(0, text="Analysing jobs...")

        try:
            raw_gaps_by_job = []
            for i, job in enumerate(jobs):
                job_id = job.get("id") or job.get("job_id")
                gaps = extract_gaps_for_job(job, profile, client)
                if gaps:
                    raw_gaps_by_job.append({
                        "job_id": job_id, "title": job["title"],
                        "company": job["company"], "gaps": gaps,
                    })
                progress.progress((i + 1) / len(jobs), text=f"Analysed {i+1}/{len(jobs)} jobs")

            if not raw_gaps_by_job:
                gaps_list, summary = [], "No significant gaps identified."
            else:
                with st.spinner("Synthesising gap report..."):
                    gaps_list = synthesise_gap_report(raw_gaps_by_job, profile, wishlist, client)
                summary = f"{len(gaps_list)} gaps identified."

            counts = {
                "high": sum(1 for g in gaps_list if g["priority"] == "high"),
                "medium": sum(1 for g in gaps_list if g["priority"] == "medium"),
                "low": sum(1 for g in gaps_list if g["priority"] == "low"),
                "total": len(gaps_list),
            }
            report = {
                "candidate_id": cid,
                "generated_date": date.today().isoformat(),
                "jobs_analyzed": [j.get("id") or j.get("job_id") for j in jobs],
                "gaps": gaps_list, "counts": counts, "summary": summary,
            }
            save_json(candidate_base(cid) / "gap_report.json", report)
            update_stage(cid, "gap_analysis_done")
            st.success(summary)
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")


# ── Page: Interview ────────────────────────────────────────────────────────

def page_interview(cid: str):
    st.title("Targeted Interview")

    gap_report = load_gap_report(cid)
    profile = load_profile(cid)

    if not gap_report.get("gaps"):
        st.warning("Run gap analysis first.")
        return

    total = len(gap_report["gaps"])
    resolved_count = sum(1 for g in gap_report["gaps"] if g.get("resolved"))
    pending = [g for g in gap_report["gaps"] if not g.get("resolved")]

    st.progress(resolved_count / total if total else 1.0,
                text=f"{resolved_count}/{total} gaps resolved")

    if not pending:
        st.success("All gaps resolved! Head to Fit Report next.")
        return

    gap = pending[0]
    badge = {"high": "🔴 HIGH", "medium": "🟡 MEDIUM", "low": "🟢 LOW"}.get(gap["priority"], "")
    st.caption(f"{badge} · {gap['gap_id']} · {len(pending)} remaining")

    with st.chat_message("assistant"):
        st.write(gap["question"])

    col1, col2 = st.columns([6, 1])
    answer = col1.chat_input("Your answer…")
    skip = col2.button("Skip", use_container_width=True)

    if skip:
        for g in gap_report["gaps"]:
            if g["gap_id"] == gap["gap_id"]:
                g["resolved"] = True
                break
        save_json(candidate_base(cid) / "gap_report.json", gap_report)
        remaining = sum(1 for g in gap_report["gaps"] if not g.get("resolved"))
        update_stage(cid, "interview_done" if remaining == 0 else "interview_in_progress")
        st.rerun()

    if answer:
        from interview import extract_profile_update, apply_enrichment
        from llm_client import LLMClient

        with st.chat_message("user"):
            st.write(answer)

        with st.spinner("Processing answer..."):
            try:
                client = LLMClient()
                enrichment = extract_profile_update(gap, answer, profile, client)
                apply_enrichment(profile, gap, answer, enrichment)

                for g in gap_report["gaps"]:
                    if g["gap_id"] == gap["gap_id"]:
                        g["resolved"] = True
                        break

                base = candidate_base(cid)
                save_json(base / "profile.json", profile)
                save_json(base / "gap_report.json", gap_report)

                remaining = sum(1 for g in gap_report["gaps"] if not g.get("resolved"))
                update_stage(cid, "interview_done" if remaining == 0 else "interview_in_progress")
                st.success(f"Noted: *{enrichment.get('extracted_summary', 'saved.')}*")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")


# ── Page: Fit Report ───────────────────────────────────────────────────────

def page_fit_report(cid: str):
    st.title("Fit Report")

    base = candidate_base(cid)
    fit_path = base / "fit_report.json"

    if fit_path.exists():
        report = json.loads(fit_path.read_text())

        st.subheader("Fit scores by role")
        for fit in sorted(report["job_title_fits"], key=lambda x: x["fit_score"], reverse=True):
            prob_color = {"high": "🟢", "medium": "🟡", "low": "🟠", "very low": "🔴"}.get(
                fit.get("reply_probability", ""), "⬜"
            )
            label = f"{fit['title']}  {prob_color} {fit.get('reply_probability', '')} reply probability"
            st.progress(fit["fit_score"] / 100, text=label)

        st.divider()
        analysis = report.get("dream_job_analysis", {})
        st.subheader(f"Dream job deep-dive: {report['dream_job']}")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**What you have**")
            for s in analysis.get("what_they_have", []):
                st.markdown(f"- {s}")
            st.markdown("**Stepping stones**")
            for r in analysis.get("stepping_stone_roles", []):
                st.markdown(f"- {r}")
        with col2:
            st.markdown("**Critical gaps**")
            for g in analysis.get("critical_gaps", []):
                with st.container(border=True):
                    st.write(f"**{g['gap']}**")
                    st.caption(f"How to close: {g['how_to_close']} · Effort: {g['effort']}")

        st.markdown(f"**Timeline:** {analysis.get('realistic_timeline', 'n/a')}")

        st.markdown("**Immediate actions**")
        for action in analysis.get("immediate_actions", []):
            st.markdown(f"- {action}")

        st.info(f"💬 {analysis.get('motivational_note', '')}")
        st.divider()

    if st.button("Generate Fit Report", type="primary"):
        from fit_report import score_job_title, dream_job_deep_analysis
        from llm_client import LLMClient

        profile = load_profile(cid)
        wishlist = load_wishlist(cid)
        client = LLMClient()

        all_titles = wishlist.get("dream_jobs", []) + wishlist.get("also_open_to", [])
        if not all_titles:
            exp = profile.get("experience", [])
            all_titles = [exp[0]["title"]] if exp else ["Software Engineer"]
        dream_title = all_titles[0]

        progress = st.progress(0, text="Scoring roles...")
        try:
            title_fits = []
            for i, title in enumerate(all_titles):
                fit = score_job_title(title, profile, wishlist, client)
                fit["title"] = title
                title_fits.append(fit)
                progress.progress((i + 1) / (len(all_titles) + 1), text=f"Scored: {title}")

            dream_fit = next((f for f in title_fits if f["title"] == dream_title), title_fits[0])
            with st.spinner("Deep analysis for dream job..."):
                dream_analysis = dream_job_deep_analysis(dream_title, profile, wishlist, dream_fit, client)

            report = {
                "candidate": profile.get("name", cid),
                "generated": date.today().isoformat(),
                "dream_job": dream_title,
                "job_title_fits": title_fits,
                "dream_job_analysis": dream_analysis,
                "summary": {
                    "best_fit_role": max(title_fits, key=lambda x: x["fit_score"])["title"],
                    "dream_job_score": dream_fit["fit_score"],
                    "dream_job_probability": dream_fit["reply_probability"],
                },
            }
            save_json(base / "fit_report.json", report)
            update_stage(cid, "fit_report_done")
            st.success("Fit report generated!")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")


# ── Page: Applications ─────────────────────────────────────────────────────

def page_applications(cid: str):
    st.title("Generate Applications")

    base = candidate_base(cid)
    apps_dir = base / "applications"

    if apps_dir.exists():
        app_dirs = [d for d in sorted(apps_dir.iterdir())
                    if d.is_dir() and (d / "meta.json").exists()]
        if app_dirs:
            st.subheader("Generated applications")
            for app_dir in app_dirs:
                meta = json.loads((app_dir / "meta.json").read_text())
                with st.expander(f"**{meta['title']}** @ {meta['company']} — {meta['status']}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Cover Letter**")
                        if (app_dir / "cover_letter.md").exists():
                            cl = (app_dir / "cover_letter.md").read_text()
                            st.download_button(
                                "Download cover letter", cl,
                                f"cover_letter_{meta['company'].lower().replace(' ', '_')}.md",
                                key=f"cl_{meta['app_id']}",
                            )
                            st.markdown(cl)
                    with col2:
                        st.markdown("**Tailored CV**")
                        if (app_dir / "cv_tailored.md").exists():
                            cv = (app_dir / "cv_tailored.md").read_text()
                            st.download_button(
                                "Download tailored CV", cv,
                                f"cv_{meta['company'].lower().replace(' ', '_')}.md",
                                key=f"cv_{meta['app_id']}",
                            )
                            st.markdown(cv)
            st.divider()

    details_dir = base / "job_screenings" / "details"
    jobs = []
    if details_dir.exists():
        for f in sorted(details_dir.glob("*.json")):
            j = json.loads(f.read_text())
            if j.get("status") == "shortlisted":
                jobs.append(j)

    if not jobs:
        st.info("No shortlisted jobs yet. Add and score jobs in Job Screening first.")
        return

    st.markdown(f"**{len(jobs)} shortlisted job(s) ready to apply for:**")
    for job in jobs:
        st.markdown(f"- {job['title']} @ {job['company']}")

    if st.button("Generate All Applications", type="primary"):
        from generate_application import generate_cover_letter, generate_tailored_cv, next_app_number
        from llm_client import LLMClient

        profile = load_profile(cid)
        apps_dir.mkdir(exist_ok=True)
        client = LLMClient()
        generated = []
        progress = st.progress(0)

        for i, job in enumerate(jobs):
            job_id = job.get("id") or job.get("job_id")
            app_num = next_app_number(apps_dir)
            company_slug = re.sub(r"[^a-z0-9]+", "_", job["company"].lower())[:20]
            title_slug = re.sub(r"[^a-z0-9]+", "_", job["title"].lower())[:20]
            folder = f"app_{app_num:03d}_{company_slug}_{title_slug}"
            app_dir = apps_dir / folder
            app_dir.mkdir(exist_ok=True)

            with st.spinner(f"Generating for {job['title']} @ {job['company']}..."):
                try:
                    (app_dir / "cover_letter.md").write_text(
                        generate_cover_letter(job, profile, client)
                    )
                    (app_dir / "cv_tailored.md").write_text(
                        generate_tailored_cv(job, profile, client)
                    )
                    meta = {
                        "app_id": folder, "job_id": job_id,
                        "title": job["title"], "company": job["company"],
                        "generated_date": date.today().isoformat(), "status": "draft",
                    }
                    (app_dir / "meta.json").write_text(json.dumps(meta, indent=2))
                    generated.append(meta)
                except Exception as e:
                    st.error(f"Error for {job['title']}: {e}")

            progress.progress((i + 1) / len(jobs))

        tracker = load_tracker(cid)
        tracker.setdefault("applications", []).extend(generated)
        save_json(base / "tracker.json", tracker)
        update_stage(cid, "applications_generated")
        st.success(f"{len(generated)} application(s) generated!")
        st.rerun()


# ── Page: Format CV ────────────────────────────────────────────────────────

def page_format_cv(cid: str):
    st.title("Format CV")
    st.markdown(
        "Reformats your tailored CV for ATS compliance and role-appropriate emphasis, "
        "then exports clean HTML. Open in browser → **File → Print → Save as PDF**."
    )

    base = candidate_base(cid)
    apps_dir = base / "applications"

    app_dirs = []
    if apps_dir.exists():
        app_dirs = [
            d for d in sorted(apps_dir.iterdir())
            if d.is_dir() and (d / "cv_tailored.md").exists() and (d / "meta.json").exists()
        ]

    if not app_dirs:
        st.info("No applications found. Generate applications first (Stage 5).")
        return

    wishlist = load_wishlist(cid)
    profile = load_profile(cid)

    for app_dir in app_dirs:
        meta = json.loads((app_dir / "meta.json").read_text())
        has_formatted = (app_dir / "cv_formatted.html").exists()
        status = "✅ formatted" if has_formatted else "⬜ not yet formatted"

        with st.expander(f"**{meta['title']}** @ {meta['company']} — {status}"):
            if has_formatted:
                html = (app_dir / "cv_formatted.html").read_text()
                md = (app_dir / "cv_formatted.md").read_text() if (app_dir / "cv_formatted.md").exists() else ""
                col1, col2 = st.columns(2)
                col1.download_button(
                    "Download HTML (print to PDF)",
                    html,
                    f"cv_{meta['company'].lower().replace(' ', '_')}.html",
                    mime="text/html",
                    key=f"html_{meta['app_id']}",
                )
                if md:
                    col2.download_button(
                        "Download Markdown",
                        md,
                        f"cv_{meta['company'].lower().replace(' ', '_')}_formatted.md",
                        key=f"fmd_{meta['app_id']}",
                    )
                with st.container():
                    st.components.v1.html(html, height=600, scrolling=True)

            if st.button(f"{'Re-format' if has_formatted else 'Format'} this CV",
                         key=f"fmt_{meta['app_id']}"):
                from format_cv import detect_role_type, reformat_cv, md_to_html
                from llm_client import LLMClient

                client = LLMClient()
                role_type = detect_role_type(meta["title"], wishlist)
                cv_md = (app_dir / "cv_tailored.md").read_text()
                candidate_name = profile.get("name", cid)

                with st.spinner(f"Reformatting for {role_type} role..."):
                    try:
                        formatted_md = reformat_cv(cv_md, role_type, meta["title"], meta["company"], client)
                        html = md_to_html(formatted_md, candidate_name)
                        (app_dir / "cv_formatted.md").write_text(formatted_md)
                        (app_dir / "cv_formatted.html").write_text(html)
                        st.success("CV formatted!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")


# ── Page: LinkedIn Profile ─────────────────────────────────────────────────

def page_linkedin(cid: str):
    st.title("LinkedIn Profile Optimiser")
    st.markdown(
        "Generates a complete, keyword-optimised LinkedIn profile ready to copy-paste: "
        "headline, About, 50 skills, experience rewrites, Open to Work settings, and Featured ideas."
    )

    base = candidate_base(cid)
    linkedin_path = base / "linkedin_profile.md"

    if linkedin_path.exists():
        content = linkedin_path.read_text()
        st.download_button(
            "Download linkedin_profile.md",
            content,
            "linkedin_profile.md",
            type="primary",
        )
        st.divider()
        st.markdown(content)
        st.divider()

    if st.button("Generate LinkedIn Profile" if not linkedin_path.exists() else "Regenerate LinkedIn Profile",
                 type="primary"):
        from linkedin_profile import (
            generate_headline, generate_about, generate_skills_section,
            generate_experience_descriptions, generate_open_to_work,
            generate_featured_suggestions, build_profile_doc,
        )
        from llm_client import LLMClient

        profile = load_profile(cid)
        wishlist = load_wishlist(cid)
        fit_path = base / "fit_report.json"
        fit_report = json.loads(fit_path.read_text()) if fit_path.exists() else {}
        client = LLMClient()
        candidate_name = profile.get("name", cid)

        progress = st.progress(0, text="Generating headline...")
        try:
            headline = generate_headline(profile, wishlist, client)
            progress.progress(1/6, text="Generating About section...")

            about = generate_about(profile, wishlist, fit_report, client)
            progress.progress(2/6, text="Generating 50 skills...")

            skills = generate_skills_section(profile, wishlist, fit_report, client)
            progress.progress(3/6, text="Rewriting experience descriptions...")

            exp_descriptions = generate_experience_descriptions(profile, wishlist, client)
            progress.progress(4/6, text="Building Open to Work settings...")

            open_to_work = generate_open_to_work(profile, wishlist)
            progress.progress(5/6, text="Generating Featured section ideas...")

            featured = generate_featured_suggestions(profile, wishlist, client)
            progress.progress(6/6, text="Done!")

            doc = build_profile_doc(
                headline, about, skills, exp_descriptions,
                open_to_work, featured, candidate_name,
            )
            linkedin_path.write_text(doc)

            tracker = load_tracker(cid)
            tracker["linkedin_profile_generated"] = date.today().isoformat()
            tracker["last_updated"] = date.today().isoformat()
            save_json(base / "tracker.json", tracker)

            st.success("LinkedIn profile generated!")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")


# ── Router ─────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(page_title="JobApply AI", page_icon="💼", layout="wide")

    if not api_key_exists():
        page_setup()
        return

    cid, page = render_sidebar()

    if page == PAGES[0] or not cid:
        page_home()
    elif page == PAGES[1]:
        page_ingest(cid)
    elif page == PAGES[2]:
        page_wishlist(cid)
    elif page == PAGES[3]:
        page_screening(cid)
    elif page == PAGES[4]:
        page_gap_analysis(cid)
    elif page == PAGES[5]:
        page_interview(cid)
    elif page == PAGES[6]:
        page_fit_report(cid)
    elif page == PAGES[7]:
        page_applications(cid)
    elif page == PAGES[8]:
        page_format_cv(cid)
    elif page == PAGES[9]:
        page_linkedin(cid)


if __name__ == "__main__":
    main()
