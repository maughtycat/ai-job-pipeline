#!/usr/bin/env python3
"""Tests for tracker write path: status validation + latest-row-only update."""
import os
import tempfile

from models import Application, ApplicationStatus, parse_status
from tracker import add_application, update_status, get_applications


def test_status_validation():
    assert parse_status("Phone Screen") is ApplicationStatus.PHONE_SCREEN
    assert parse_status("Rejcted") is None          # typo must not poison reads
    assert parse_status("Interview") is ApplicationStatus.INTERVIEW


def test_update_latest_row_only():
    path = tempfile.mktemp(suffix=".db")
    try:
        add_application(Application(company="SameCo", role="Role A",
                                    date_applied="2026-01-01"), path=path)
        add_application(Application(company="SameCo", role="Role B",
                                    date_applied="2026-02-01"), path=path)
        assert update_status("SameCo", "Interview", path=path) is True
        apps = {a.role: a for a in get_applications(path=path)}
        assert apps["Role B"].status is ApplicationStatus.INTERVIEW  # latest flipped
        assert apps["Role A"].status is ApplicationStatus.APPLIED    # history kept
        assert update_status("NoSuchCo", "Rejected", path=path) is False  # honest miss
    finally:
        if os.path.exists(path):
            os.unlink(path)


if __name__ == "__main__":
    test_status_validation()
    test_update_latest_row_only()
    print("OK: 2 tests, 6 assertions passed")
