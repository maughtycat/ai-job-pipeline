
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
    """Conserved-flow funnel: continuing stage on top of each column, that
    stage's drop-offs stacked directly beneath it, so every ribbon runs node
    edge to node edge. Stage labels sit above their node, drop-off labels
    beside their node, never over a ribbon. Two semantic colors: blue =
    advanced, red = dropped out (red/blue is a colorblind-safe pair; the old
    red/green was not).
    shortcut: heights are floored at 6px because 414:1 makes the 1-offer node
    sub-pixel; floor rounding can shift ribbon junctions by up to ~8px,
    invisible at these opacities. Labels carry the exact values. """
    W, H, NW, TOP, GAP, FLOOR, M = 960, 560, 14, 80, 18, 8, 44
    STAGE_Y = 64
    n = 5
    xs = [M + i * (W - 2 * M - NW) / (n - 1) for i in range(n)]
    total = stats["applications"]
    # budget: below title band (80), above footnote band (60), minus the two
    # stack gaps col1 needs for its two drop-offs
    scale = (H - TOP - 60 - 2 * GAP) / total

    def h(v):
        return max(v * scale, FLOOR)

    # columns: (stage label, continuing value, [drop-off (label, value)...])
    # every column's values sum to the flow entering it (conserved)
    cols = [
        ("Applied", total,
         [("Never answered", stats["never_responded"]),
          ("Rejected, no conversation", stats["rejected_no_conversation"])]),
        ("Conversation", stats["conversations"],
         [("Stopped at screen", stats["screen_only"])]),
        ("Reached HM", stats["hm_rounds"] + stats["deep_rounds"],
         [("Stopped at HM", stats["hm_rounds"])]),
        ("Deep round", stats["deep_rounds"],
         [("Rejected after deep", stats["deep_rounds"] - stats["offer"])]),
        ("Offer accepted", stats["offer"], []),
    ]

    # node heights: a continuing node is at least as tall as what it emits,
    # so ribbon source spans partition it exactly even after floor rounding
    node_h = []
    for label, val, drops in cols:
        out_h = h(val)
        node_h.append(out_h)
    for j in range(len(cols) - 1):
        emitted = node_h[j + 1] + sum(h(d[1]) for d in cols[j][2])
        node_h[j] = max(node_h[j], emitted)

    # place nodes: each column holds its continuing node on top, plus the
    # drop-offs released by the PREVIOUS column's flows stacked beneath
    placed = []   # list per column: [(kind, label, value, x, y, height), ...]
    for j, (label, val, drops) in enumerate(cols):
        y = TOP
        col = [("stage", label, val, xs[j], y, node_h[j])]
        y += node_h[j]
        if j > 0:
            for dlabel, dval in cols[j - 1][2]:
                y += GAP
                col.append(("drop", dlabel, dval, xs[j], y, h(dval)))
                y += h(dval)
        placed.append(col)

    ribbons, marks, texts = [], [], []

    def ribbon(x0, y0, x1, y1, hh, fill, opacity):
        m = (x0 + x1) / 2
        ribbons.append(
            f'<path d="M{x0:.1f},{y0:.1f} C{m:.1f},{y0:.1f} {m:.1f},{y1:.1f} '
            f'{x1:.1f},{y1:.1f} L{x1:.1f},{y1 + hh:.1f} C{m:.1f},{y1 + hh:.1f} '
            f'{m:.1f},{y0 + hh:.1f} {x0:.1f},{y0 + hh:.1f} Z" '
            f'fill="{fill}" opacity="{opacity}"/>')

    # ribbons: leaving the continuing node of column j, arriving at the
    # continuing node and each drop-off of column j+1, cursor from node top
    for j in range(len(cols) - 1):
        label, val, drops = cols[j]
        src_node = placed[j][0]
        cursor = src_node[4]
        targets = [(cols[j + 1][0], node_h[j + 1], placed[j + 1][0][4], "#58a6ff", 0.60)]
        for k, (dlabel, dval) in enumerate(drops):
            t = placed[j + 1][1 + k]
            targets.append((dlabel, h(dval), t[4], "#f85149", 0.45))
        x0 = xs[j] + NW
        for tlabel, th, ty, color, op in targets:
            ribbon(x0, cursor, xs[j + 1], ty, th, color, op)
            cursor += th

    # nodes
    for col in placed:
        for kind, label, val, x, y, hh in col:
            color = "#58a6ff" if kind == "stage" else "#f85149"
            marks.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{NW}" '
                         f'height="{hh:.1f}" rx="3" fill="{color}"/>')

    # labels: stages above the node (first starts at its x, last ends at its
    # right edge so it can never clip), drop-offs beside the node (left side
    # when the right side would run off the canvas)
    for j, col in enumerate(placed):
        for i, (kind, label, val, x, y, hh) in enumerate(col):
            value = f"{val:g}"
            if kind == "stage":
                if j == 0:
                    anchor, lx = "start", x
                elif j == len(placed) - 1:
                    anchor, lx = "end", x + NW
                else:
                    anchor, lx = "middle", x + NW / 2
                texts.append(
                    f'<text x="{lx:.1f}" y="{STAGE_Y}" text-anchor="{anchor}" '
                    f'font-family="Helvetica,Arial" font-size="14" fill="#e6edf3">'
                    f'<tspan font-weight="bold">{label} </tspan>'
                    f'<tspan fill="#8b949e">{value}</tspan></text>')
            else:
                full = f"{label} {value}"
                est = len(full) * 6.1
                if hh >= 40:
                    # big drop-off: label beside the node, vertically centered
                    anchor = "start"
                    lx = min(x + NW + 8, W - 4 - est)
                    ly = y + hh / 2 + 4
                else:
                    # small drop-off: label beneath the node, clear of every
                    # ribbon; clamped so it can never leave the canvas
                    anchor = "start"
                    lx = min(x, W - 4 - est)
                    ly = y + hh + 15
                texts.append(
                    f'<text x="{lx:.1f}" y="{ly:.1f}" '
                    f'text-anchor="{anchor}" font-family="Helvetica,Arial" '
                    f'font-size="12" fill="#c9d1d9">{label} '
                    f'<tspan fill="#e6edf3" font-weight="bold">{value}</tspan></text>')

    title = (f'{stats["applications"]} applications → {stats["conversations"]} '
             f'conversations → {stats["hm_rounds"] + stats["deep_rounds"]} HM rounds → '
             f'{stats["deep_rounds"]} deep rounds → {stats["offer"]} offer')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" '
        f'role="img" aria-label="Job search funnel: {title}">'
        f'<rect width="{W}" height="{H}" fill="#0f1117" rx="8"/>'
        f'<text x="{M}" y="28" font-family="Helvetica,Arial" font-size="15" '
        f'font-weight="bold" fill="#58a6ff">{title}</text>'
        + "".join(ribbons) + "".join(marks) + "".join(texts)
        + f'<text x="{M}" y="{H - 14}" font-family="Helvetica,Arial" font-size="11" '
          f'fill="#c9d1d9">{stats["date_start"]} to {stats["date_end"]}, '
          f'{stats["weeks"]} weeks. Blue = advanced. Red = dropped out.</text>'
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
