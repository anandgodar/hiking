#!/usr/bin/env python3
"""
Draft dashboard: which trails are live vs. still need work, and exactly what.

A trail is published on the site only when it is route-complete: a real GPS
path and a distance, with the `_status` draft flag removed. This report lists,
per state, which trails are LIVE and which are DRAFT, and for each draft shows
the precise fields still missing — so you can finish them efficiently.

Usage:
  python3 scripts/draft-status.py                 # all states with data
  python3 scripts/draft-status.py virginia        # one state
  python3 scripts/draft-status.py --missing virginia   # only show what's missing
"""

import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "website" / "src" / "data"
NON_TRAIL = {"blog", "guides", "_rejected"}


def needs(d):
    """Return the list of fields a trail still needs to go live."""
    t = (d.get("trails") or [{}])[0]
    stats = t.get("stats") or {}
    geo = t.get("geo") or {}
    missing = []
    if not (isinstance(geo.get("path"), list) and geo.get("path")):
        missing.append("GPS path (add gpx-downloads/<slug>.gpx → gpx-to-geo.py)")
    if not stats.get("distance"):
        missing.append("distance")
    if not stats.get("gain"):
        missing.append("elevation gain")
    if not (t.get("difficulty") or stats.get("difficulty")):
        missing.append("difficulty")
    if d.get("_status"):
        missing.append("remove _status flag (after verifying facts)")
    # Recommended (not blocking publish, but flagged):
    soft = []
    if not d.get("mountain_hero"):
        soft.append("hero image")
    if not d.get("generated_description"):
        soft.append("description")
    return missing, soft


def is_live(d):
    t = (d.get("trails") or [{}])[0]
    geo = t.get("geo") or {}
    stats = t.get("stats") or {}
    return (not d.get("_status")
            and isinstance(geo.get("path"), list) and geo.get("path")
            and isinstance(stats.get("distance"), (int, float)) and stats.get("distance") > 0)


def states_with_data(argv):
    if argv:
        return argv
    return sorted(p.name for p in DATA.iterdir()
                  if p.is_dir() and p.name not in NON_TRAIL)


def main():
    args = sys.argv[1:]
    only_missing = "--missing" in args
    args = [a for a in args if a != "--missing"]

    grand_live = grand_draft = 0
    for state in states_with_data(args):
        files = sorted(glob.glob(str(DATA / state / "*.json")))
        if not files:
            continue
        live, drafts = [], []
        for f in files:
            d = json.loads(Path(f).read_text())
            if not d.get("name"):
                continue
            (live if is_live(d) else drafts).append((f, d))
        grand_live += len(live)
        grand_draft += len(drafts)

        print(f"\n=== {state} ===  LIVE {len(live)}  ·  DRAFT {len(drafts)}")
        if not only_missing and live:
            print("  live:", ", ".join(d["name"] for _, d in live[:30])
                  + (" …" if len(live) > 30 else ""))
        for f, d in drafts:
            missing, soft = needs(d)
            print(f"  ✗ {d['name']}")
            print(f"      needs: {', '.join(missing) if missing else '—'}")
            if soft:
                print(f"      also:  {', '.join(soft)}")

    print(f"\n{'='*50}")
    print(f"TOTAL  ·  LIVE {grand_live}  ·  DRAFT {grand_draft}")
    print("Only LIVE (route-complete) trails appear on the public site.")


if __name__ == "__main__":
    main()
