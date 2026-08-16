"""Material generator — creates tailored resume bullets and cover letters."""

from llm import call_llm_json, call_llm
from models import GeneratedMaterials, JobPosting, Profile


RESUME_SYSTEM = """Generate tailored resume bullet points AND answers to application questions for a job application.
Return valid JSON:
{
  "resume_bullets": ["bullet1", "bullet2", ...],
  "short_answers": {
    "question1": "answer",
    "question2": "answer"
  }
}
Write 4-6 bullets. Be specific with numbers and outcomes. Match the posting's language.
For short answers: answer EVERY question from the job posting. Be specific, use real examples from the candidate's experience. 2-4 sentences per answer. Sound human, not AI-generated."""


COVER_LETTER_SYSTEM = """Write a cover letter in the candidate's voice.
Guidelines:
- 3 paragraphs max, under 250 words
- Opening: specific connection to the company/role
- Middle: 2-3 relevant accomplishments with numbers
- Closing: direct, confident, no hedging
- Match the tone of the reference text provided
- No em dashes, no AI-default verbs (leverage, empower, seamless)
- Sound like a human talking about their work"""


def generate_materials(
    posting: JobPosting, profile: Profile
) -> GeneratedMaterials:
    """Generate tailored application materials for a job posting."""
    profile_text = f"""
Candidate: {profile.name}, {profile.title}
Skills: {', '.join(s.get('name', '') + ' (' + s.get('level', '') + ')' for s in profile.skills)}
Experience: {'; '.join(e.get('company', '') + ' - ' + e.get('role', '') + ': ' + '; '.join(e.get('highlights', [])) for e in profile.experience)}
"""

    posting_text = f"""
Company: {posting.company}
Role: {posting.role}
Required skills: {', '.join(posting.required_skills)}
Responsibilities: {'; '.join(posting.responsibilities[:5])}
Application questions: {'; '.join(posting.application_questions) if posting.application_questions else 'None listed — generate standard answers (Why this company?, Tell us about yourself)'}
"""

    # Generate resume bullets
    resume_prompt = f"CANDIDATE:\n{profile_text}\n\nJOB POSTING:\n{posting_text}"
    resume_data = call_llm_json(resume_prompt, system=RESUME_SYSTEM)

    # Generate cover letter
    tone_instruction = ""
    if profile.reference_tone:
        tone_instruction = f"\n\nReference text (match this tone and voice):\n{profile.reference_tone[:1000]}"

    cover_prompt = f"Write a cover letter for this application.\n\nCANDIDATE:\n{profile_text}\n\nJOB POSTING:\n{posting_text}{tone_instruction}"
    cover_letter = call_llm(cover_prompt, system=COVER_LETTER_SYSTEM)

    return GeneratedMaterials(
        resume_bullets=resume_data.get("resume_bullets", []),
        cover_letter=cover_letter,
        short_answers=resume_data.get("short_answers", {}),
    )
