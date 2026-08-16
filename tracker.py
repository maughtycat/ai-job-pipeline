"""Application tracker — SQLite-backed tracking with RESEA export."""

import csv
import io
import sqlite3
from datetime import datetime
from typing import Optional

from models import Application, ApplicationStatus


DB_PATH = "applications.db"


def get_db(path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            date_applied TEXT,
            status TEXT DEFAULT 'Applied',
            fit_score INTEGER,
            salary_range TEXT,
            target_ask TEXT,
            notes TEXT,
            follow_up_date TEXT
        )
    """)
    conn.commit()
    return conn


def add_application(app: Application, path: str = DB_PATH) -> int:
    db = get_db(path)
    cursor = db.execute(
        """INSERT INTO applications
           (company, role, date_applied, status, fit_score, salary_range, target_ask, notes, follow_up_date)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            app.company,
            app.role,
            app.date_applied or datetime.now().strftime("%Y-%m-%d"),
            app.status.value,
            app.fit_score,
            app.salary_range,
            app.target_ask,
            app.notes,
            app.follow_up_date,
        ),
    )
    db.commit()
    return cursor.lastrowid or 0


def update_status(
    company: str, status: str, notes: str = "", path: str = DB_PATH
) -> bool:
    db = get_db(path)
    if notes:
        db.execute(
            "UPDATE applications SET status = ?, notes = notes || ? WHERE company = ?",
            (status, f"\n{notes}", company),
        )
    else:
        db.execute("UPDATE applications SET status = ? WHERE company = ?", (status, company))
    db.commit()
    return db.total_changes > 0


def get_applications(
    status: Optional[str] = None, path: str = DB_PATH
) -> list[Application]:
    db = get_db(path)
    if status:
        rows = db.execute(
            "SELECT * FROM applications WHERE status = ? ORDER BY date_applied DESC",
            (status,),
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM applications ORDER BY date_applied DESC").fetchall()
    return [
        Application(
            company=r["company"],
            role=r["role"],
            date_applied=r["date_applied"],
            status=ApplicationStatus(r["status"]),
            fit_score=r["fit_score"],
            salary_range=r["salary_range"],
            target_ask=r["target_ask"],
            notes=r["notes"],
            follow_up_date=r["follow_up_date"],
        )
        for r in rows
    ]


def get_stats(path: str = DB_PATH) -> dict:
    db = get_db(path)
    total = db.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
    by_status = dict(
        db.execute("SELECT status, COUNT(*) FROM applications GROUP BY status").fetchall()
    )
    avg_score = db.execute(
        "SELECT AVG(fit_score) FROM applications WHERE fit_score IS NOT NULL"
    ).fetchone()[0]
    return {
        "total": total,
        "by_status": by_status,
        "avg_fit_score": round(avg_score, 1) if avg_score else None,
    }


def export_resea(path: str = DB_PATH) -> str:
    """Export applications in RESEA-compliant CSV format."""
    apps = get_applications(path=path)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Company", "Position", "Date Applied", "Status", "Method"])
    for app in apps:
        writer.writerow([
            app.company,
            app.role,
            app.date_applied,
            app.status.value,
            "Online",
        ])
    return output.getvalue()
