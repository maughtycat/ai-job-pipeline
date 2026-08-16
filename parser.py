"""Job posting parser — extracts structured data from URLs or raw text."""

import requests
from bs4 import BeautifulSoup

from llm import call_llm_json
from models import JobPosting


def fetch_url(url: str) -> str:
    """Fetch readable text from a job posting URL."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; JobPipeline/1.0)"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


SYSTEM_PROMPT = """You extract structured job posting data from text.
Return valid JSON with these fields:
{
  "company": "string",
  "role": "string",
  "location": "string",
  "remote_type": "remote|hybrid|onsite",
  "salary_range": "string (empty if not listed)",
  "required_skills": ["string"],
  "preferred_skills": ["string"],
  "years_experience": "string",
  "responsibilities": ["string"],
  "application_questions": ["string (questions the applicant must answer, e.g. 'Why are you interested in this role?', 'Describe a time you failed')"]
}
If a field is not mentioned, use an empty string or empty list.
Look for application questions in sections like "How to apply", "Application questions", or inline in the posting."""


def parse_posting(text: str, url: str = "") -> JobPosting:
    """Parse job posting text into a structured JobPosting."""
    prompt = f"Extract structured data from this job posting:\n\n{text[:4000]}"
    data = call_llm_json(prompt, system=SYSTEM_PROMPT)

    return JobPosting(
        company=data.get("company", "Unknown"),
        role=data.get("role", "Unknown"),
        location=data.get("location", ""),
        remote_type=data.get("remote_type", ""),
        salary_range=data.get("salary_range", ""),
        required_skills=data.get("required_skills", []),
        preferred_skills=data.get("preferred_skills", []),
        years_experience=data.get("years_experience", ""),
        responsibilities=data.get("responsibilities", []),
        application_questions=data.get("application_questions", []),
        url=url,
        raw_text=text[:2000],
    )


def parse_input(source: str) -> JobPosting:
    """Parse from URL or raw text. Auto-detects which."""
    if source.startswith("http://") or source.startswith("https://"):
        text = fetch_url(source)
        return parse_posting(text, url=source)
    return parse_posting(source)
