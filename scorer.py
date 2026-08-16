"""Relevance scorer — evaluates fit between a job posting and user profile."""

from llm import call_llm_json
from models import FitScore, JobPosting, Profile


SYSTEM_PROMPT = """You evaluate how well a job posting matches a candidate's profile.
Be realistic: many postings list preferred skills as "required." Weight actual skill
overlap and experience relevance more heavily than checkbox requirements.

Return valid JSON:
{
  "score": 0-100,
  "breakdown": {
    "skills": 0-100,
    "experience": 0-100,
    "location": 0-100,
    "salary": 0-100
  },
  "reasoning": "1-2 sentence explanation",
  "red_flags": ["list of concerns or dealbreakers"],
  "recommendation": "Build" or "Skip",
  "key_terms": ["5-8 specific terms from the posting that influenced scoring"]
}
70+ = Build. 50-69 = Borderline. Below 50 = Skip.
key_terms should be actual phrases from the posting like AI agents, prompt engineering,
cross-functional collaboration — not generic words like experience."""


def score_job(posting: JobPosting, profile: Profile) -> FitScore:
    """Score a job posting against the user's profile."""
    profile_text = f"""
Candidate: {profile.name}, {profile.title}
Skills: {', '.join(s.get('name', '') + ' (' + s.get('level', '') + ')' for s in profile.skills)}
Experience: {'; '.join(e.get('company', '') + ' - ' + e.get('role', '') + ' (' + str(e.get('years', '')) + ' yrs)' for e in profile.experience)}
Preferences: {profile.preferences}
Dealbreakers: {'; '.join(profile.dealbreakers)}
"""

    posting_text = f"""
Company: {posting.company}
Role: {posting.role}
Location: {posting.location} ({posting.remote_type})
Salary: {posting.salary_range}
Required skills: {', '.join(posting.required_skills)}
Preferred skills: {', '.join(posting.preferred_skills)}
Experience: {posting.years_experience}
"""

    prompt = f"CANDIDATE:\n{profile_text}\n\nJOB POSTING:\n{posting_text}"
    data = call_llm_json(prompt, system=SYSTEM_PROMPT)

    return FitScore(
        score=data.get("score", 0),
        breakdown=data.get("breakdown", {}),
        reasoning=data.get("reasoning", ""),
        red_flags=data.get("red_flags", []),
        recommendation=data.get("recommendation", ""),
        key_terms=data.get("key_terms", []),
    )
