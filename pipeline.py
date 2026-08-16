#!/usr/bin/env python3
"""AI Job Application Pipeline — CLI orchestrator."""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml

from models import Application, ApplicationStatus, Profile
from parser import parse_input
from scorer import score_job
from generator import generate_materials
from tracker import add_application, update_status, get_stats, export_resea


def load_profile(path: str = "profile.yaml") -> Profile:
    with open(path) as f:
        data = yaml.safe_load(f)
    return Profile(
        name=data.get("name", ""),
        title=data.get("title", ""),
        skills=data.get("skills", []),
        experience=data.get("experience", []),
        preferences=data.get("preferences", {}),
        dealbreakers=data.get("dealbreakers", []),
        reference_tone=data.get("reference_tone", ""),
    )


def cmd_analyze(args):
    """Parse, score, and generate materials for a job posting."""
    profile = load_profile(args.profile)

    print(f"Analyzing: {args.source[:80]}...")
    posting = parse_input(args.source)
    print(f"  Parsed: {posting.company} — {posting.role}")

    print("  Scoring fit...")
    fit = score_job(posting, profile)
    print(f"  Fit score: {fit.score}/100")
    if fit.red_flags:
        print(f"  Red flags: {'; '.join(fit.red_flags)}")

    print("  Generating materials...")
    materials = generate_materials(posting, profile)

    # Output
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save results as JSON
    results = {
        "posting": {
            "company": posting.company,
            "role": posting.role,
            "location": posting.location,
            "remote_type": posting.remote_type,
            "salary_range": posting.salary_range,
            "required_skills": posting.required_skills,
            "preferred_skills": posting.preferred_skills,
            "years_experience": posting.years_experience,
            "responsibilities": posting.responsibilities,
            "application_questions": posting.application_questions,
            "raw_text": posting.raw_text,
        },
        "fit": {
            "score": fit.score,
            "breakdown": fit.breakdown,
            "reasoning": fit.reasoning,
            "red_flags": fit.red_flags,
            "recommendation": fit.recommendation,
            "key_terms": fit.key_terms,
        },
        "materials": {
            "resume_bullets": materials.resume_bullets,
            "cover_letter": materials.cover_letter,
            "short_answers": materials.short_answers,
        },
    }

    json_path = output_dir / f"{posting.company.lower().replace(' ', '_')}.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved to {json_path}")

    # Print summary
    print(f"\n{'='*50}")
    print(f"{posting.company} — {posting.role}")
    print(f"Fit: {fit.score}/100 | {fit.reasoning}")
    print(f"{'='*50}")
    print(f"\nResume bullets:")
    for b in materials.resume_bullets:
        print(f"  • {b}")
    print(f"\nCover letter:\n{materials.cover_letter}")
    if materials.short_answers:
        print(f"\nShort answers:")
        for q, a in materials.short_answers.items():
            print(f"  Q: {q}")
            print(f"  A: {a}")


def cmd_track(args):
    """Track applications."""
    if args.track_action == "add":
        app = Application(
            company=args.company,
            role=args.role,
            date_applied=args.date or datetime.now().strftime("%Y-%m-%d"),
            fit_score=args.score,
        )
        app_id = add_application(app)
        print(f"Added: {args.company} — {args.role} (id: {app_id})")

    elif args.track_action == "status":
        update_status(args.company, args.status, notes=args.notes or "")
        print(f"Updated: {args.company} → {args.status}")

    elif args.track_action == "list":
        from tracker import get_applications
        apps = get_applications(status=args.filter)
        for app in apps:
            print(f"  [{app.status.value}] {app.company} — {app.role} ({app.date_applied})")

    elif args.track_action == "stats":
        stats = get_stats()
        print(f"Total applications: {stats['total']}")
        print(f"By status: {json.dumps(stats['by_status'], indent=2)}")
        if stats["avg_fit_score"]:
            print(f"Average fit score: {stats['avg_fit_score']}")

    elif args.track_action == "export":
        csv_data = export_resea()
        out_path = Path(args.output or "resea_export.csv")
        out_path.write_text(csv_data)
        print(f"RESEA export saved to {out_path}")


def main():
    parser = argparse.ArgumentParser(
        description="AI Job Application Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pipeline.py analyze "https://example.com/job-posting"
  python pipeline.py analyze "We are looking for a Python engineer..."
  python pipeline.py track add --company Acme --role "AI Engineer"
  python pipeline.py track status --company Acme --status Interview
  python pipeline.py track stats
  python pipeline.py track export
        """,
    )
    parser.add_argument("--profile", default="profile.yaml", help="Path to profile YAML")

    sub = parser.add_subparsers(dest="command")

    # analyze
    p_analyze = sub.add_parser("analyze", help="Analyze a job posting")
    p_analyze.add_argument("source", help="Job posting URL or text")
    p_analyze.add_argument("--output", "-o", default="examples/output", help="Output directory")

    # track
    p_track = sub.add_parser("track", help="Track applications")
    track_sub = p_track.add_subparsers(dest="track_action")

    p_add = track_sub.add_parser("add", help="Add an application")
    p_add.add_argument("--company", required=True)
    p_add.add_argument("--role", required=True)
    p_add.add_argument("--date")
    p_add.add_argument("--score", type=int)

    p_status = track_sub.add_parser("status", help="Update status")
    p_status.add_argument("--company", required=True)
    p_status.add_argument("--status", required=True)
    p_status.add_argument("--notes")

    p_list = track_sub.add_parser("list", help="List applications")
    p_list.add_argument("--filter", help="Filter by status")

    p_stats = track_sub.add_parser("stats", help="Show statistics")

    p_export = track_sub.add_parser("export", help="Export for RESEA audit")
    p_export.add_argument("--output", "-o", default="resea_export.csv")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Load .env if present
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    if args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "track":
        cmd_track(args)


if __name__ == "__main__":
    main()
