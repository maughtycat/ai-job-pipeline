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


def load_results():
    results = []
    for f in sorted(CACHE_DIR.glob("*.json")):
        with open(f) as fh:
            data = json.load(fh)
            data["_filename"] = f.stem
            results.append(data)
    return results


results = load_results()

st.title("AI Job Application Pipeline")
st.caption(
    "An AI-powered tool that parses job postings, scores relevance, "
    "and generates tailored application materials. "
    "[GitHub](https://github.com/maughtycat/ai-job-pipeline)"
)

tab_demo, tab_stats = st.tabs(["Pipeline Demo", "Application Stats"])

with tab_demo:
    st.header("Pipeline Demo")
    st.markdown(
        "Select a cached job posting to see how the pipeline analyzes it. "
        "No API calls — these are pre-canned results from real applications."
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

        # Recommendation banner
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
            st.write(f"Salary: {posting.get('salary_range', 'Not listed')}")
            if posting.get("required_skills"):
                st.write(f"Required: {', '.join(posting['required_skills'][:5])}")

            if fit.get("breakdown"):
                st.markdown("**Score Breakdown:**")
                cols = st.columns(4)
                for i, (cat, val) in enumerate(fit["breakdown"].items()):
                    cols[i].metric(cat.capitalize(), f"{val}/100")

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
    st.markdown(
        "Aggregated data from 279 tailored applications over 2.5 months."
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Applications", "279")
    col2.metric("Per Week", "25")
    col3.metric("Recruiter Screens", "10")
    col4.metric("HM Interviews", "8")

    col5, col6 = st.columns(2)
    col5.metric("Recruiter to HM Rate", "80%")
    col6.metric("Avg Salary Range", "$118K-$165K")

    st.divider()

    st.subheader("Pipeline Funnel")
    funnel = [
        {"Stage": "Applied", "Count": 279},
        {"Stage": "Recruiter Screen", "Count": 10},
        {"Stage": "HM Interview", "Count": 8},
        {"Stage": "Deep Dive / Take-home", "Count": 1},
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

st.divider()
st.caption(
    "Built by Kara Novotny | "
    "[GitHub](https://github.com/maughtycat/ai-job-pipeline) | "
    "[Portfolio](https://maughtycat.github.io/portfolio/) | "
    "Human-in-the-loop: tool handles research and drafting, human handles judgment and submission"
)
