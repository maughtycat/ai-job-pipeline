"""Job posting parser — extracts structured data from URLs or raw text."""

import requests
from bs4 import BeautifulSoup

from llm import call_llm_json
from models import JobPosting, ParsedPosting


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
    prompt = f"Extract structured data from this job posting:\n\n{text[:12000]}"
    data = call_llm_json(prompt, system=SYSTEM_PROMPT)
    # None values fall back to model defaults instead of failing the field
    data = {k: v for k, v in data.items() if v is not None}
    parsed = ParsedPosting.model_validate(data)

    return JobPosting(
        company=parsed.company,
        role=parsed.role,
        location=parsed.location,
        remote_type=parsed.remote_type,
        salary_range=parsed.salary_range,
        required_skills=parsed.required_skills,
        preferred_skills=parsed.preferred_skills,
        years_experience=parsed.years_experience,
        responsibilities=parsed.responsibilities,
        application_questions=parsed.application_questions,
        url=url,
        raw_text=text,
    )


def parse_input(source: str) -> JobPosting:
    """Parse from URL or raw text. Auto-detects which."""
    if source.startswith("http://") or source.startswith("https://"):
        text = fetch_url(source)
        return parse_posting(text, url=source)
    return parse_posting(source)
