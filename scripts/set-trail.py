#!/usr/bin/env python3
"""
Set a trail's manual fields and (optionally) publish it — no hand-editing JSON.

After a real GPX has given a trail its route (path + distance + gain), the only
things left are usually difficulty, type, parking, and the human verification
sign-off. This sets those from the command line and, with --publish, removes the
`_status` flag so the trail goes live on the next build.

--publish is refused unless the trail is actually route-complete (real GPS path
+ distance), so you can't accidentally publish an empty stub.

Usage:
  python3 scripts/set-trail.py <state> <slug> [options]

Options:
  --difficulty X     Easy | Moderate | Hard | Strenuous
  --type X           "Out & Back" | "Loop" | "Point to Point"
  --distance N       miles (normally auto-filled from GPX; override if needed)
  --gain N           feet (normally auto-filled from GPX)
  --time N           hours round trip
  --parking "X"      parking_info text
  --fee "X"          parking fee
  --hero URL         mountain_hero image URL
  --publish          remove the _status flag (requires a complete route)

Example:
  python3 scripts/set-trail.py virginia mount-rogers-va \
      --difficulty Moderate --type "Out & Back" --parking "Massie Gap" --publish
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "website" / "src" / "data"


def is_route_complete(trail):
    geo = trail.get("geo") or {}
    stats = trail.get("stats") or {}
    path = geo.get("path")
    dist = stats.get("distance")
    return (isinstance(path, list) and len(path) > 0
            and isinstance(dist, (int, float)) and dist > 0)


def main():
    p = argparse.ArgumentParser(description="Set a trail's manual fields / publish")
    p.add_argument("state")
    p.add_argument("slug")
    p.add_argument("--difficulty")
    p.add_argument("--type", dest="type_")
    p.add_argument("--distance", type=float)
    p.add_argument("--gain", type=float)
    p.add_argument("--time", type=float)
    p.add_argument("--parking")
    p.add_argument("--fee")
    p.add_argument("--hero")
    p.add_argument("--publish", action="store_true")
    args = p.parse_args()

    f = DATA / args.state / f"{args.slug}.json"
    if not f.exists():
        sys.exit(f"❌ Not found: {f.relative_to(ROOT)}")

    d = json.loads(f.read_text())
    trails = d.get("trails") or []
    if not trails:
        sys.exit("❌ Trail file has no trails[] entry")
    t = trails[0]
    t.setdefault("stats", {})
    t.setdefault("parking_details", {})

    changes = []
    if args.difficulty:
        t["difficulty"] = args.difficulty
        t["stats"]["difficulty"] = args.difficulty
        changes.append(f"difficulty={args.difficulty}")
    if args.type_:
        t["type"] = args.type_
        changes.append(f"type={args.type_}")
    if args.distance is not None:
        t["stats"]["distance"] = args.distance
        changes.append(f"distance={args.distance}")
    if args.gain is not None:
        t["stats"]["gain"] = args.gain
        changes.append(f"gain={args.gain}")
    if args.time is not None:
        t["stats"]["time"] = args.time
        changes.append(f"time={args.time}")
    if args.parking:
        t["parking_info"] = args.parking
        changes.append("parking_info")
    if args.fee:
        t["parking_details"]["fee"] = args.fee
        changes.append("fee")
    if args.hero:
        d["mountain_hero"] = args.hero
        changes.append("mountain_hero")

    published = False
    if args.publish:
        if not is_route_complete(t):
            sys.exit("❌ Refusing to publish: trail has no route yet. Add a real "
                     "GPX (gpx-downloads/<slug>.gpx) and run the pipeline first.")
        if d.pop("_status", None) is not None:
            changes.append("removed _status (PUBLISHED)")
            published = True
        else:
            changes.append("already published")

    if not changes:
        print("No changes specified. See --help for options.")
        return

    f.write_text(json.dumps(d, indent=2) + "\n")
    print(f"✅ {args.state}/{args.slug}: {', '.join(changes)}")
    if published:
        print("   This trail will appear on the site after the next build.")
    print(f"   Re-run enrichment: python3 scripts/run-pipeline.py --state {args.state}")


if __name__ == "__main__":
    main()
