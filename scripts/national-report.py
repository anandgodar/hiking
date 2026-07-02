#!/usr/bin/env python3
"""
Nationwide inventory health report: every state at a glance.

One table for the whole dataset — LIVE vs DRAFT per state, the top reasons
drafts are held, and a duplicate guard (same name or <0.3 mi apart within a
state — duplicate pages cannibalize each other in search). Also written as
machine-readable JSON to pipeline-reports/national-report.json.

Usage:
  python3 scripts/national-report.py
"""

import glob
import json
import math
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "website" / "src" / "data"
NON_TRAIL = {"blog", "guides", "_rejected"}


def haversine_mi(a, b):
    R = 3959
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dlat = math.radians(b[0] - a[0]); dlon = math.radians(b[1] - a[1])
    h = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(h))


def is_live(d):
    t = (d.get("trails") or [{}])[0]
    return (not d.get("_status")
            and (t.get("geo") or {}).get("path")
            and ((t.get("stats") or {}).get("distance") or 0) > 0)


def draft_reason(d):
    t = (d.get("trails") or [{}])[0]
    if not (t.get("geo") or {}).get("path"):
        return "no route"
    if not ((t.get("stats") or {}).get("distance") or 0) > 0:
        return "no distance"
    if d.get("_status", "").startswith("demoted"):
        return d["_status"].split("—", 1)[-1].strip()[:40]
    return "quality review"


def main():
    states = sorted(p.name for p in DATA.iterdir()
                    if p.is_dir() and p.name not in NON_TRAIL)
    report = {"date": str(date.today()), "states": {}, "duplicates": []}
    tot_live = tot_draft = 0

    print(f"{'STATE':<16} {'LIVE':>5} {'DRAFT':>6}  TOP DRAFT REASONS")
    print("-" * 64)
    for state in states:
        live = draft = 0
        reasons = Counter()
        recs = []
        for f in sorted(glob.glob(str(DATA / state / "*.json"))):
            d = json.loads(Path(f).read_text())
            if not d.get("name"):
                continue
            if d.get("lat") is not None:
                recs.append((Path(f).name, d["name"].lower().strip(),
                             d["lat"], d["lon"]))
            if is_live(d):
                live += 1
            else:
                draft += 1
                reasons[draft_reason(d)] += 1
        # duplicate guard within the state
        for i in range(len(recs)):
            for j in range(i + 1, len(recs)):
                a, b = recs[i], recs[j]
                if a[1] == b[1] or haversine_mi((a[2], a[3]), (b[2], b[3])) < 0.3:
                    report["duplicates"].append(
                        {"state": state, "files": [a[0], b[0]]})
        tot_live += live; tot_draft += draft
        top = ", ".join(f"{r} ({n})" for r, n in reasons.most_common(2)) or "—"
        print(f"{state:<16} {live:>5} {draft:>6}  {top}")
        report["states"][state] = {"live": live, "draft": draft,
                                   "draft_reasons": dict(reasons)}

    print("-" * 64)
    print(f"{'TOTAL':<16} {tot_live:>5} {tot_draft:>6}   across {len(states)} state(s)")
    if report["duplicates"]:
        print(f"\n⚠️  {len(report['duplicates'])} possible duplicate pair(s) "
              f"(SEO cannibalization risk):")
        for dup in report["duplicates"][:10]:
            print(f"   {dup['state']}: {dup['files'][0]} <-> {dup['files'][1]}")
    else:
        print("✅ No duplicate trails detected.")

    out = ROOT / "pipeline-reports" / "national-report.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"\nJSON: pipeline-reports/national-report.json")


if __name__ == "__main__":
    main()
