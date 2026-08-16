# AI Job Application Pipeline

An AI-powered tool that parses job postings, scores relevance against your profile, generates tailored resume bullets and cover letters, and tracks your applications.

Built and used during my own job search: 279 tailored applications, 25 per week, 8 hiring manager interviews.

## Live Demo

[Try the dashboard](https://ai-job-pipeline.streamlit.app) — browse pre-canned pipeline results and application stats. No API key needed.

## Quick Start

```bash
git clone https://github.com/maughtycat/ai-job-pipeline.git
cd ai-job-pipeline
pip install -r requirements.txt
cp .env.example .env  # Add your OpenRouter API key
python pipeline.py analyze "https://example.com/job-posting"
```

## How It Works

The pipeline has three stages:

1. **Parse** — Extracts structured data (company, role, skills, salary) from job posting URLs or pasted text using an LLM
2. **Score** — Evaluates fit against your profile with reasoning and red flags
3. **Generate** — Creates tailored resume bullets and cover letters in your voice

A tracker logs every application with status, fit score, and notes. Exportable for RESEA unemployment audits.

### Human-in-the-Loop

This is not a "set it and forget it" automation. I review every output before submitting. The tool handles the research and drafting. I handle the judgment and submission. Application forms have anti-bot measures, inconsistent fields, and subtle requirements that an automated agent would miss.

## Architecture

```
Input (URL/text) → Parse → Score → Generate → Output (JSON + materials)
                                                      ↓
                                              Application Tracker (SQLite)
                                                      ↓
                                              Dashboard (Streamlit)
```

## Tech Stack

| Technology | Why |
|-----------|-----|
| **Python** | Strongest skill, AI-augmented workflow runs in Python, most LLM SDKs are Python-first |
| **OpenRouter** | User brings their own API key. No surprise billing. Supports dozens of models. |
| **SQLite** | Zero config, portable, sufficient for single-user pipeline. The database is one file. |
| **Pydantic** | Validates LLM structured output. Catches garbage before it reaches the pipeline. |
| **Streamlit** | Fastest path from CLI to visual demo. Not the most scalable, but this isn't a SaaS. |
| **argparse** | Stdlib. No click, no typer, no dependency needed for a CLI that does four things. |

## Project Structure

```
ai-job-pipeline/
├── pipeline.py        # CLI orchestrator
├── parser.py          # Job posting extraction
├── scorer.py          # Fit evaluation
├── generator.py       # Material generation
├── tracker.py         # SQLite tracking + RESEA export
├── models.py          # Shared dataclasses
├── llm.py             # OpenRouter client wrapper
├── dashboard.py       # Streamlit dashboard
├── profile.yaml       # Your skills and experience
├── examples/          # Sample outputs
└── requirements.txt
```

## License

MIT
