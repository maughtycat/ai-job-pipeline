
#!/usr/bin/env python3
"""Derive final job-search funnel stats from private tracking data.

Reads status.json (path given at runtime; never bundled with the repo),
classifies each held conversation by furthest stage, asserts the funnel
chain, and writes aggregate-only artifacts: final_stats.json + sankey.svg.

Usage:
    python3 final_stats.py --status /path/to/status.json \
        --overrides /path/to/overrides.json --out-dir examples
"""
import argparse, json, re, sys
from pathlib import Path

EXCLUDE_PATTERNS = [
    re.compile(r"did not happen", re.I),
    re.compile(r"^2026-\d\d-\d\d\s*-\s*rejected$", re.I),
    re.compile(r"^rejected 2026-\d\d-\d\d$", re.I),
    re.compile(r"rejection email received", re.I),
]
DEEP_RE = re.compile(r"take-?home|deep dive|technical panel", re.I)
HM_RE = re.compile(r"hiring manager|\bhm screen\b|\bhm interview\b|"
                   r"hm screen completed|two hms|\bhm\b.*(completed|interview)", re.I)
SCREEN_RE = re.compile(r"recruiter screen|phone screen|intro call", re.I)


def classify(entry, overrides):
    """Furthest held stage: 'screen'|'hm'|'deep', 'excluded', or None."""
    if entry.get("status") == "PTO":
        return None
    iv = (entry.get("interview") or "").strip()
    if iv in ("-", ""):
        return None
    name = entry["company"]
    if name in overrides:
        return overrides[name]
    if any(p.search(iv) for p in EXCLUDE_PATTERNS):
        return "excluded"
    text = iv + " " + (entry.get("notes") or "")
    if DEEP_RE.search(text):
        return "deep"
    if HM_RE.search(text):
        return "hm"
    if SCREEN_RE.search(text):
        return "screen"
    return "excluded"  # interview field populated but no held-conversation evidence


def funnel_counts(entries, overrides):
    ct = {"applications": 0, "conversations": 0, "screen_only": 0, "hm_rounds": 0,
          "deep_rounds": 0, "offer": 0, "never_responded": 0,
          "rejected_no_conversation": 0, "rejected_total": 0,
          "no_conversation": 0, "pto_skipped": 0, "excluded": 0}
    for e in entries:
        if e.get("status") == "PTO":
            ct["pto_skipped"] += 1
            continue
        ct["applications"] += 1
        if e["status"] == "Rejected":
            ct["rejected_total"] += 1
        stage = classify(e, overrides)
        if stage in ("screen", "hm", "deep"):
            ct["conversations"] += 1
            ct[{"screen": "screen_only", "hm": "hm_rounds",
                "deep": "deep_rounds"}[stage]] += 1
            if e["status"] == "Accepted":
                ct["offer"] += 1
        else:
            # no held conversation — 'excluded' is a sub-counter, NOT a
            # separate flow, or applications != no_conversation + conversations
            if stage == "excluded":
                ct["excluded"] += 1
            if e["status"] == "Applied":
                ct["never_responded"] += 1
            elif e["status"] == "Rejected":
                ct["rejected_no_conversation"] += 1
    ct["no_conversation"] = ct["never_responded"] + ct["rejected_no_conversation"]
    return ct


def chain_ok(ct):
    """Every flow in, every flow out. Any drift means the data moved."""
    checks = [
        ct["screen_only"] + ct["hm_rounds"] + ct["deep_rounds"] == ct["conversations"],
        ct["no_conversation"] + ct["conversations"] == ct["applications"],
        ct["no_conversation"] == ct["never_responded"] + ct["rejected_no_conversation"],
        ct["deep_rounds"] >= ct["offer"],
        ct["rejected_total"] == ct["rejected_no_conversation"]
        + (ct["conversations"] - ct["offer"]),
    ]
    return all(checks)


def build_sankey(stats):
    """Linear funnel Sankey. Floors exist because the scale is 414:1 —
    without them the 1-offer node is sub-pixel. Junction mismatch <=2px is
    invisible at 0.3 opacity; do not chase exact conservation with floors on."""
    W, H, PAD_T, PAD_B, NODE_W, GAP = 960, 470, 52, 64, 14, 30
    scale = (H - PAD_T - PAD_B) / stats["applications"]
    cols = [
        ("Applied", stats["applications"],
         [("Never answered", stats["never_responded"]),
          ("Rejected, no conversation", stats["rejected_no_conversation"])]),
        ("Conversation", stats["conversations"],
         [("Stopped at screen", stats["screen_only"])]),
        ("HM round", stats["hm_rounds"] + stats["deep_rounds"],
         [("Stopped at HM", stats["hm_rounds"])]),
        ("Deep round", stats["deep_rounds"],
         [("Rejected after deep", stats["deep_rounds"] - stats["offer"])]),
        ("Offer accepted", stats["offer"], []),
    ]
    n = len(cols)
    M = 40
    xs = [M + i * (W - 2 * M - NODE_W) / (n - 1) for i in range(n)]
    band = lambda v: max(v * scale, 2)
    node = lambda v: max(v * scale, 3)
    parts, links, labels = [], [], []
    for i, (label, val, drops) in enumerate(cols):
        h = node(val)
        y = PAD_T
        parts.append(f'<rect x="{xs[i]:.1f}" y="{y:.1f}" width="{NODE_W}" '
                     f'height="{h:.1f}" rx="3" fill="#58a6ff"/>')
        labels.append(f'<text x="{xs[i]:.1f}" y="{y - 14:.1f}" font-family="Helvetica,Arial" '
                      f'font-size="14" font-weight="bold" fill="#e6edf3">{label} {val}</text>')
        if i < n - 1:
            # continuing flow is target-height, top-aligned; drops peel the
            # remaining bands below it
            h_next = node(cols[i + 1][1])
            x0, x1 = xs[i] + NODE_W, xs[i + 1]
            cx = (x0 + x1) / 2
            links.append(
                f'<path d="M{x0:.1f},{y:.1f} C{cx:.1f},{y:.1f} {cx:.1f},{y:.1f} '
                f'{x1:.1f},{y:.1f} L{x1:.1f},{y + h_next:.1f} C{cx:.1f},{y + h_next:.1f} '
                f'{cx:.1f},{y + h_next:.1f} {x0:.1f},{y + h_next:.1f} Z" '
                f'fill="#3fb950" opacity="0.3"/>')
        # drops peel from the bottom bands, side-by-side so labels never stack
        cursor = y + band(val) - sum(band(d[1]) for d in drops)
        cursor = max(cursor, y)
        for k, (dl, dv) in enumerate(drops):
            dh = band(dv)
            dx = xs[i] + NODE_W + 44 + k * (NODE_W + 108)
            rect_y = cursor
            parts.append(f'<rect x="{dx:.1f}" y="{rect_y:.1f}" width="{NODE_W}" '
                         f'height="{dh:.1f}" rx="3" fill="#f85149"/>')
            labels.append(f'<text x="{dx + NODE_W / 2:.1f}" y="{rect_y + dh + 15:.1f}" '
                          f'text-anchor="middle" font-family="Helvetica,Arial" font-size="11" '
                          f'fill="#8b949e">{dl} {dv}</text>')
            x_a, x_b = xs[i] + NODE_W, dx
            cx = (x_a + x_b) / 2
            links.append(
                f'<path d="M{x_a:.1f},{rect_y:.1f} C{cx:.1f},{rect_y:.1f} {cx:.1f},{rect_y:.1f} '
                f'{x_b:.1f},{rect_y:.1f} L{x_b:.1f},{rect_y + dh:.1f} C{cx:.1f},{rect_y + dh:.1f} '
                f'{cx:.1f},{rect_y + dh:.1f} {x_a:.1f},{rect_y + dh:.1f} Z" '
                f'fill="#f85149" opacity="0.22"/>')
            cursor += dh
    title = (f'{stats["applications"]} applications → {stats["conversations"]} conversations → '
             f'{stats["hm_rounds"] + stats["deep_rounds"]} HM rounds → '
             f'{stats["deep_rounds"]} deep rounds → {stats["offer"]} offer')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" '
        f'role="img" aria-label="Job search funnel: {title}">'
        f'<rect width="{W}" height="{H}" fill="#0f1117" rx="8"/>'
        f'<text x="{M}" y="30" font-family="Helvetica,Arial" font-size="15" '
        f'font-weight="bold" fill="#58a6ff">{title}</text>'
        + "".join(links) + "".join(parts) + "".join(labels)
        + f'<text x="{M}" y="{H - 20}" font-family="Helvetica,Arial" font-size="11" '
          f'fill="#8b949e">{stats["date_start"]} to {stats["date_end"]}, '
          f'{stats["weeks"]} weeks. Green = advanced. Red = dropped out.</text>'
        f'</svg>')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", required=True, help="path to private status.json")
    ap.add_argument("--overrides", help="path to private overrides.json")
    ap.add_argument("--out-dir", default="examples")
    args = ap.parse_args()

    entries = json.loads(Path(args.status).read_text(encoding="utf-8"))
    overrides = (json.loads(Path(args.overrides).read_text(encoding="utf-8"))
                 if args.overrides else {})
    ct = funnel_counts(entries, overrides)
    if not chain_ok(ct):
        print("FUNNEL CHAIN BROKEN — data changed? "
              f"{json.dumps(ct, indent=2)}", file=sys.stderr)
        sys.exit(1)

    dates = [e["date"] for e in entries if e.get("status") != "PTO"]
    from datetime import date
    d1, d2 = min(dates), max(dates)
    weeks = round((date.fromisoformat(d2) - date.fromisoformat(d1)).days / 7, 1)
    conv = ct["conversations"]
    stats = {
        "generated": "2026-10-19",
        "source": "private tracking data; aggregates only, no company names",
        "date_start": d1, "date_end": d2, "weeks": weeks,
        "avg_per_week": round(ct["applications"] / weeks, 1),
        "unique_companies": len({e["company"] for e in entries
                                 if e.get("status") != "PTO"}),
        **ct,
        "hm_plus": ct["hm_rounds"] + ct["deep_rounds"],
        "rates": {
            "application_to_conversation": f"{conv / ct['applications'] * 100:.1f}%",
            "conversation_to_hm": f"{(ct['hm_rounds'] + ct['deep_rounds']) / conv * 100:.0f}%",
            "application_to_offer": f"{ct['offer'] / ct['applications'] * 100:.2f}%",
        },
    }
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "final_stats.json").write_text(json.dumps(stats, indent=2) + "\n",
                                          encoding="utf-8")
    (out / "sankey.svg").write_text(build_sankey(stats), encoding="utf-8")

    print(f"Applications: {ct['applications']} ({ct['pto_skipped']} PTO days skipped)")
    print(f"Conversations: {conv}  (screen-only {ct['screen_only']}, "
          f"reached HM {ct['hm_rounds'] + ct['deep_rounds']}, "
          f"deep {ct['deep_rounds']}, offer {ct['offer']})")
    print(f"No conversation: {ct['no_conversation']} (never answered "
          f"{ct['never_responded']}, rejected w/o conv {ct['rejected_no_conversation']})")
    print(f"Rejected total: {ct['rejected_total']} | Excluded ambiguous: {ct['excluded']}")
    print("Funnel check: OK")
    print(f"Wrote {out / 'final_stats.json'}")
    print(f"Wrote {out / 'sankey.svg'}")


if __name__ == "__main__":
    main()
