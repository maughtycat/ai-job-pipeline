"""Streamlit dashboard for AI Job Application Pipeline.

Run locally: streamlit run dashboard.py
Deploy: push to GitHub, connect to Streamlit Cloud
"""

import json
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="AI Job Application Pipeline",
    page_icon="🤖",
    layout="wide",
)

CACHE_DIR = Path("examples/output")
TRACKING_FILE = Path("examples/tracking_data.json")


def load_results():
    results = []
    for f in sorted(CACHE_DIR.glob("*.json")):
        with open(f) as fh:
            data = json.load(fh)
            data["_filename"] = f.stem
            results.append(data)
    return results


def load_tracking_data():
    if TRACKING_FILE.exists():
        with open(TRACKING_FILE) as f:
            return json.load(f)
    return None


results = load_results()
tracking = load_tracking_data()

st.title("AI Job Application Pipeline")
st.caption(
    "An AI-powered tool that parses job postings, scores relevance, "
    "and generates tailored application materials. "
    "[GitHub](https://github.com/maughtycat/ai-job-pipeline)"
)

tab_demo, tab_stats, tab_tracking = st.tabs(["Pipeline Demo", "Application Stats", "Tracking"])

with tab_demo:
    st.header("Pipeline Demo")
    st.markdown(
        "Select a cached job posting to see how the pipeline analyzes it. "
        "No API calls — these are sample results from real applications."
    )

    if not results:
        st.warning("No cached results found in examples/output/")
    else:
        options = {
            f"{r['posting']['company']} — {r['posting']['role']}": r
            for r in results
        }
        selected = st.selectbox("Select a job posting", list(options.keys()))
        data = options[selected]

        posting = data["posting"]
        fit = data["fit"]
        materials = data["materials"]

        # Outcome badge
        outcome = fit.get("outcome", "")
        if outcome:
            if "HM" in outcome or "Take-home" in outcome or "Deep dive" in outcome:
                st.success(f"**Actual Outcome:** {outcome}")
            else:
                st.info(f"**Actual Outcome:** {outcome}")
        rec = fit.get("recommendation", "")
        if rec == "Build":
            st.success(f"**Recommendation: {rec}** — Worth applying")
        elif rec == "Skip":
            st.error(f"**Recommendation: {rec}** — Not a good fit")
        else:
            st.warning("**Recommendation: Borderline**")

        col1, col2 = st.columns([1, 2])
        with col1:
            score = fit["score"]
            st.metric("Fit Score", f"{score}/100")
            st.markdown(f"*{fit['reasoning']}*")

            if fit.get("red_flags"):
                st.markdown("**Red Flags:**")
                for flag in fit["red_flags"]:
                    st.warning(flag)

        with col2:
            st.markdown("**Job Posting**")
            st.write(f"**{posting.get('company', '')}** — {posting.get('role', '')}")
            st.write(f"Location: {posting.get('location', '')} ({posting.get('remote_type', '')})")
            salary = posting.get('salary_range', 'Not listed')
            st.markdown(f"Salary (USD): {salary}")
            if posting.get("required_skills"):
                st.write(f"Required: {', '.join(posting['required_skills'][:5])}")

        # Key Terms — what drove the scoring
        if fit.get("key_terms"):
            st.markdown("**Key Terms (from posting):**")
            term_html = " ".join(
                f'<span style="background: #1f4e79; color: white; padding: 2px 8px; '
                f'border-radius: 4px; font-size: 13px; margin: 2px;">{t}</span>'
                for t in fit["key_terms"]
            )
            st.markdown(term_html, unsafe_allow_html=True)

        # Expandable raw job posting text
        raw_text = posting.get("raw_text", "")
        if raw_text:
            with st.expander("View full job posting text"):
                st.markdown(raw_text)

        st.divider()
        st.subheader("Generated Materials")
        st.caption("All outputs are first drafts. Review, edit, and personalize before submission. Many employers request AI-free application materials.")

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Resume Bullets**")
            for bullet in materials.get("resume_bullets", []):
                st.markdown(f"- {bullet}")

        with col_b:
            st.markdown("**Cover Letter**")
            st.markdown(materials.get("cover_letter", "No cover letter generated."))

        if materials.get("short_answers"):
            st.subheader("Short Answers")
            for question, answer in materials["short_answers"].items():
                st.markdown(f"**{question}**")
                st.markdown(answer)

with tab_stats:
    st.header("Application Stats")
    agg = tracking["aggregate"] if tracking else {}
    st.markdown(
        f"Aggregated data from {agg.get('total_applied', 279)} tailored applications "
        f"over {agg.get('weeks_active', 11)} weeks."
    )

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Applications", str(agg.get("total_applied", 279)))
    col2.metric("Per Week", str(agg.get("per_week", 25)))
    col3.metric("Recruiter Screens", str(agg.get("recruiter_screens", 10)))
    col4.metric("HM Interviews", str(agg.get("hm_interviews", 8)))
    col5.metric("Recruiter to HM Rate", agg.get("conversion_rate", "80%"))

    st.divider()

    st.subheader("Pipeline Funnel")
    funnel = [
        {"Stage": "Applied", "Count": agg.get("total_applied", 279)},
        {"Stage": "Recruiter Screen", "Count": agg.get("recruiter_screens", 10)},
        {"Stage": "HM Interview", "Count": agg.get("hm_interviews", 8)},
        {"Stage": "Deep Dive / Take-home", "Count": agg.get("deep_dives", 1)},
    ]
    st.dataframe(funnel, use_container_width=True, hide_index=True)

    st.subheader("Applications by Month")
    timeline = [
        {"Month": "June 2026", "Applications": 112},
        {"Month": "July 2026", "Applications": 116},
        {"Month": "August 2026 (partial)", "Applications": 51},
    ]
    st.dataframe(timeline, use_container_width=True, hide_index=True)

    st.subheader("Fit Scores (from demo)")
    score_data = [
        {"Company": r["posting"]["company"], "Score": r["fit"]["score"], "Recommendation": r["fit"].get("recommendation", "")}
        for r in results
    ]
    st.dataframe(score_data, use_container_width=True, hide_index=True)

with tab_tracking:
    st.header("Application Tracking")
    st.markdown(
        "The pipeline includes a SQLite-backed tracker that logs every application "
        "with status, fit score, salary range, and notes. Below is a curated sample "
        "showing the tracking in action."
    )

    if tracking:
        agg = tracking["aggregate"]

        # Status metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Applied", str(agg["total_applied"]))
        c2.metric("Recruiter Screens", str(agg["recruiter_screens"]))
        c3.metric("HM Interviews", str(agg["hm_interviews"]))
        c4.metric("Conversion Rate", agg["conversion_rate"])

        st.divider()

        # Funnel visualization
        st.subheader("Pipeline Funnel")
        funnel_data = {
            "Stage": ["Applied", "Recruiter Screen", "HM Interview", "Deep Dive"],
            "Count": [agg["total_applied"], agg["recruiter_screens"], agg["hm_interviews"], agg["deep_dives"]],
        }
        st.bar_chart(funnel_data, x="Stage", y="Count", horizontal=True, color="#58a6ff")

        # Weekly activity
        st.subheader("Weekly Activity")
        weekly = tracking.get("weekly_activity", [])
        if weekly:
            st.bar_chart(
                {w["week"]: w["applied"] for w in weekly},
                horizontal=False,
                color="#3fb950",
            )

        st.divider()

        # Sample applications
        st.subheader("Sample Applications")
        st.caption("Representative entries from the full tracker. Status reflects outcome after pipeline processing.")
        samples = tracking.get("sample_applications", [])
        if samples:
            st.dataframe(samples, use_container_width=True, hide_index=True)

        st.divider()
        st.caption(
            "**RESEA Compliance:** The tracker exports a RESEA-compliant CSV with company, "
            "position, date applied, and method for every application. Used to satisfy "
            "unemployment audit requirements without reconstructing search history from memory."
        )
    else:
        st.info("Tracking data not found. Add examples/tracking_data.json to enable this view.")

st.divider()
st.caption(
    "Built by Kara Novotny | "
    "[GitHub](https://github.com/maughtycat/ai-job-pipeline) | "
    "[Portfolio](https://maughtycat.github.io/portfolio/) | "
    "Human-in-the-loop: tool handles research and drafting, human handles judgment and submission"
)
