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

# Load cached results
CACHE_DIR = Path("examples/output")


@st.cache_data
def load_results():
    results = []
    for f in sorted(CACHE_DIR.glob("*.json")):
        with open(f) as fh:
            data = json.load(fh)
            data["_filename"] = f.stem
            results.append(data)
    return results


results = load_results()

# Header
st.title("AI Job Application Pipeline")
st.caption(
    "An AI-powered tool that parses job postings, scores relevance, "
    "and generates tailored application materials. "
    "[GitHub](https://github.com/maughtycat/ai-job-pipeline)"
)

# Tabs
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
        # Build selection options
        options = {
            f"{r['posting']['company']} — {r['posting']['role']} (Score: {r['fit']['score']})": r
            for r in results
        }
        selected = st.selectbox("Select a job posting", list(options.keys()))
        data = options[selected]

        posting = data["posting"]
        fit = data["fit"]
        materials = data["materials"]

        # Fit Score
        col1, col2 = st.columns([1, 2])
        with col1:
            score = fit["score"]
            color = (
                "green" if score >= 70 else "orange" if score >= 50 else "red"
            )
            st.metric("Fit Score", f"{score}/100")
            st.markdown(f":{color}[{fit['reasoning']}]")

            if fit.get("red_flags"):
                st.subheader("Red Flags")
                for flag in fit["red_flags"]:
                    st.warning(flag)

        with col2:
            # Posting details
            st.subheader("Job Posting")
            st.json(posting, expanded=False)

            # Score breakdown
            if fit.get("breakdown"):
                st.subheader("Score Breakdown")
                st.bar_chart(fit["breakdown"])

        # Generated Materials
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

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Applications", "279")
    col2.metric("Per Week", "25")
    col3.metric("Recruiter Screens", "10")
    col4.metric("HM Interviews", "8")

    col5, col6, col7 = st.columns(3)
    col5.metric("Recruiter → HM Rate", "80%")
    col6.metric("Avg Salary Range", "$118K–$165K")
    col7.metric("Currently Interviewing", "1")

    st.divider()

    # Score distribution from cached results
    st.subheader("Fit Score Distribution (Sample)")
    scores = [r["fit"]["score"] for r in results]
    st.bar_chart({"Score": scores})

    # Role mix
    st.subheader("Applications by Role Type")
    role_data = {"AI": 151, "Engineering": 134, "Technical Writer": 67}
    st.bar_chart(role_data)

    # Timeline
    st.subheader("Applications Over Time")
    timeline_data = {
        "Month": ["June", "July", "August"],
        "Applications": [112, 116, 51],
    }
    st.bar_chart(timeline_data)

    # Pipeline funnels
    st.subheader("Pipeline Funnel")
    funnel_data = {
        "Stage": [
            "Applied",
            "Recruiter Screen",
            "HM Interview",
            "Deep Dive",
        ],
        "Count": [279, 10, 8, 1],
    }
    st.bar_chart(funnel_data)

# Footer
st.divider()
st.caption(
    "Built by Kara Novotny | "
    "[GitHub](https://github.com/maughtycat/ai-job-pipeline) | "
    "[Portfolio](https://maughtycat.github.io/portfolio/) | "
    "Human-in-the-loop: tool handles research and drafting, human handles judgment and submission"
)
