#!/usr/bin/env python3
"""
Generate nearby_peaks internal links for trails that have none.

Better internal linking improves retention (more places to click) and SEO
(crawlable, related-content link graph). For each trail missing nearby_peaks,
this finds the closest OTHER trails in the same state by real great-circle
distance (from each trail's actual lat/lon) and links them. No data is
invented — distances are computed, names/slugs/elevations come from the
target files.

Idempotent: trails that already have nearby_peaks are left untouched unless
--force is passed.

Usage:
  python3 scripts/generate-nearby-peaks.py                 # all trail states
  python3 scripts/generate-nearby-peaks.py maine vermont   # only these states
  python3 scripts/generate-nearby-peaks.py --force         # rebuild all
Options:
  --max N      max links per trail (default 4)
  --radius MI  only link peaks within MI miles (default 75)
"""

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "website" / "src" / "data"


def trail_states():
    cfg = ROOT / "pipeline.config.json"
    if cfg.exists():
        slugs = [s["slug"] for s in json.loads(cfg.read_text()).get("states", [])]
        if slugs:
            return slugs
    skip = {"blog", "guides"}
    return [p.name for p in DATA.iterdir() if p.is_dir() and p.name not in skip]


def haversine_miles(lat1, lon1, lat2, lon2):
    R = 3959
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def load_state(state):
    """Return list of trail dicts with the fields we need for linking."""
    trails = []
    for f in sorted((DATA / state).glob("*.json")):
        try:
            d = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue
        if d.get("lat") is None or d.get("lon") is None:
            continue
        trails.append({
            "file": f,
            "name": d.get("name"),
            "slug": d.get("slug", f.stem),
            "state_slug": d.get("state_slug", state),
            "elevation": d.get("elevation"),
            "lat": d["lat"],
            "lon": d["lon"],
            "has_peaks": bool(d.get("nearby_peaks")),
        })
    return trails


def nearest(target, others, max_n, radius):
    scored = []
    for o in others:
        if o["slug"] == target["slug"]:
            continue
        dist = haversine_miles(target["lat"], target["lon"], o["lat"], o["lon"])
        if dist <= radius:
            scored.append((dist, o))
    scored.sort(key=lambda x: x[0])
    out = []
    for dist, o in scored[:max_n]:
        out.append({
            "name": o["name"],
            "slug": o["slug"],
            "state_slug": o["state_slug"],
            "elevation": o["elevation"],
            "distance_miles": round(dist, 1),
        })
    return out


def process_state(state, force, max_n, radius):
    trails = load_state(state)
    updated = 0
    for t in trails:
        if t["has_peaks"] and not force:
            continue
        peaks = nearest(t, trails, max_n, radius)
        if not peaks:
            print(f"  · no peers within {radius} mi: {t['slug']}")
            continue
        d = json.loads(t["file"].read_text())
        d["nearby_peaks"] = peaks
        with open(t["file"], "w") as fh:
            json.dump(d, fh, indent=2)
            fh.write("\n")
        updated += 1
        print(f"  ✅ {t['slug']}: linked {len(peaks)} peak(s) "
              f"({', '.join(p['slug'] for p in peaks)})")
    return updated


def main():
    args = sys.argv[1:]
    force = "--force" in args
    max_n = 4
    radius = 75.0
    states = []
    i = 0
    rest = [a for a in args if a != "--force"]
    while i < len(rest):
        if rest[i] == "--max":
            max_n = int(rest[i + 1]); i += 2
        elif rest[i] == "--radius":
            radius = float(rest[i + 1]); i += 2
        else:
            states.append(rest[i]); i += 1
    states = states or trail_states()

    total = 0
    for state in states:
        print(f"▶ {state}")
        total += process_state(state, force, max_n, radius)
    print(f"\nUpdated {total} trail(s) with nearby_peaks.")


if __name__ == "__main__":
    main()
