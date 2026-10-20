
#!/usr/bin/env python3
"""Tests for final_stats.py — funnel classification + chain invariants."""
from final_stats import classify, funnel_counts, chain_ok

FIXTURE = [
    {"company": "PauseCo", "status": "PTO", "interview": ""},          # skipped
    {"company": "SilentCo", "status": "Applied", "interview": "-"},    # never answered
    {"company": "SilentCo2", "status": "Applied", "interview": ""},    # never answered
    {"company": "RejCo", "status": "Rejected", "interview": "-"},      # rejected, no conv
    {"company": "ScreenCo", "status": "Rejected",
     "interview": "2026-07-02 (recruiter screen: R. Crui, Agency)"},
    {"company": "HmCo", "status": "Rejected",
     "interview": "2026-06-26 (hiring manager + PM)"},
    {"company": "OvrCo", "status": "Rejected",
     "interview": "2026-08-01 phone screen (R. Crui). hm decision pending"},
    {"company": "DeepCo", "status": "Rejected",
     "interview": "screen -> HM -> Take-home submitted -> deep dive call"},
    {"company": "WinCo", "status": "Accepted",
     "interview": "screen -> TECHNICAL PANEL 75min -> final presentation"},
    {"company": "GhostCo", "status": "Rejected",
     "interview": "2026-10-06 intro call - DID NOT HAPPEN"},
    {"company": "DateCo", "status": "Rejected", "interview": "2026-08-14 - Rejected"},
    {"company": "DateCo2", "status": "Rejected", "interview": "Rejected 2026-08-27"},
    {"company": "MailCo", "status": "Rejected",
     "interview": "2026-09-09: Rejection email received"},
]
OVERRIDES = {"OvrCo": "screen"}   # mirrors Applications/overrides.json


def test_classification():
    c = {e["company"]: classify(e, OVERRIDES) for e in FIXTURE}
    assert c["PauseCo"] is None            # PTO never classified
    assert c["SilentCo"] is None and c["SilentCo2"] is None
    assert c["RejCo"] is None
    assert c["ScreenCo"] == "screen"
    assert c["HmCo"] == "hm"
    assert c["OvrCo"] == "screen"          # override beats regex
    assert c["DeepCo"] == "deep"
    assert c["WinCo"] == "deep"
    assert c["GhostCo"] == "excluded"
    assert c["DateCo"] == "excluded" and c["DateCo2"] == "excluded"
    assert c["MailCo"] == "excluded"


def test_funnel_chain():
    ct = funnel_counts(FIXTURE, OVERRIDES)
    assert ct["pto_skipped"] == 1
    assert ct["applications"] == 12            # 13 rows minus 1 PTO
    assert ct["conversations"] == 5            # ScreenCo, OvrCo, HmCo, DeepCo, WinCo
    assert ct["screen_only"] == 2              # ScreenCo + OvrCo (override)
    assert ct["hm_rounds"] == 1                # HmCo
    assert ct["deep_rounds"] == 2              # DeepCo + WinCo
    assert ct["offer"] == 1                    # WinCo
    assert ct["never_responded"] == 2          # SilentCo, SilentCo2
    assert ct["excluded"] == 4                 # GhostCo, DateCo, DateCo2, MailCo
    # excluded entries had no held conversation, so they land in the
    # no-conversation flow, and all four are Rejected status:
    assert ct["rejected_no_conversation"] == 5 # RejCo + the 4 excluded
    assert ct["no_conversation"] == 7          # 2 never + 5 rejected-no-conv
    assert ct["rejected_total"] == 9           # every Rejected row
    # chain identities (also asserted by chain_ok below):
    assert ct["screen_only"] + ct["hm_rounds"] + ct["deep_rounds"] == ct["conversations"]
    assert ct["no_conversation"] + ct["conversations"] == ct["applications"]  # 7+5=12
    assert ct["never_responded"] + ct["rejected_no_conversation"] == ct["no_conversation"]
    assert ct["rejected_no_conversation"] + (ct["conversations"] - ct["offer"]) == ct["rejected_total"]
    assert chain_ok(ct)


if __name__ == "__main__":
    test_classification()
    test_funnel_chain()
    print("OK: 2 tests, 25 assertions passed")
