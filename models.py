"""Shared data models for the AI Job Application Pipeline."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ApplicationStatus(Enum):
    APPLIED = "Applied"
    SCREENING = "Screening"
    PHONE_SCREEN = "Phone Screen"
    INTERVIEW = "Interview"
    REJECTED = "Rejected"
    OFFER = "Offer"
    WITHDRAWN = "Withdrawn"


@dataclass
class JobPosting:
    company: str
    role: str
    location: str = ""
    remote_type: str = ""  # remote, hybrid, onsite
    salary_range: str = ""
    required_skills: list[str] = field(default_factory=list)
    preferred_skills: list[str] = field(default_factory=list)
    years_experience: str = ""
    responsibilities: list[str] = field(default_factory=list)
    application_questions: list[str] = field(default_factory=list)
    url: str = ""
    raw_text: str = ""


@dataclass
class FitScore:
    score: int  # 0-100
    breakdown: dict[str, int] = field(default_factory=dict)  # category -> score
    reasoning: str = ""
    red_flags: list[str] = field(default_factory=list)
    recommendation: str = ""  # "Build" or "Skip"


@dataclass
class GeneratedMaterials:
    resume_bullets: list[str] = field(default_factory=list)
    cover_letter: str = ""
    short_answers: dict[str, str] = field(default_factory=dict)


@dataclass
class Application:
    company: str
    role: str
    date_applied: str = ""
    status: ApplicationStatus = ApplicationStatus.APPLIED
    fit_score: Optional[int] = None
    salary_range: str = ""
    target_ask: str = ""
    notes: str = ""
    follow_up_date: str = ""


@dataclass
class Profile:
    name: str = ""
    title: str = ""
    skills: list[dict] = field(default_factory=list)
    experience: list[dict] = field(default_factory=list)
    preferences: dict = field(default_factory=dict)
    dealbreakers: list[str] = field(default_factory=list)
    reference_tone: str = ""
