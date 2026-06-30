#!/usr/bin/env python3
"""
Scaffold a new trail JSON file with the correct schema.

This does NOT invent trail facts. It creates the folder (if needed) and a stub
file with every field in the right place — safety-critical facts (coordinates,
elevation, distance, difficulty, source URL) are left null/blank for you to fill
in from an authoritative source (NPS / USFS / State Parks / USGS).

Because required fields start empty, the new trail is intentionally flagged by
validate-trail-data.js until you complete it — a forcing function for accuracy.
Once the real facts are in, the pipeline fills the derived parts (SEO,
nearby_peaks) and audits GPS quality.

Usage:
  python3 scripts/new-trail.py <state-slug> <trail-slug> [--name "Display Name"]

Example:
  python3 scripts/new-trail.py colorado mount-elbert --name "Mount Elbert"
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "website" / "src" / "data"


def state_meta(state_slug):
    """Pull the state's display name + data_sources default from the config."""
    cfg_path = ROOT / "pipeline.config.json"
    data_sources = None
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text())
        for s in cfg.get("states", []):
            if s["slug"] == state_slug:
                data_sources = s.get("data_sources")
                break
    display = state_slug.replace("-", " ").title()
    return display, data_sources


def stub(state_slug, trail_slug, name, data_sources):
    state_name, _ = state_meta(state_slug)
    ds = dict(data_sources) if data_sources else {
        "verified_by": "",
        "primary_url": "",
        "elevation_source": "USGS Benchmark",
        "gps_source": "USGS Topographic Map",
    }
    ds.setdefault("verification_date", "")  # YYYY-MM-DD when you verify it
    return {
        "_status": "draft — fill the null/empty fields from an official source, "
                   "then remove this key",
        "name": name or "",
        "slug": trail_slug,
        "state": state_name,
        "state_slug": state_slug,
        "elevation": None,            # summit elevation in feet (USGS benchmark)
        "lat": None,                  # summit/destination latitude
        "lon": None,                  # summit/destination longitude
        "mountain_hero": "",          # image URL
        "tags": [],                   # e.g. ["14er", "views"]
        "trails": [
            {
                "name": "",           # route name, e.g. "Northeast Ridge"
                "difficulty": "",     # Easy | Moderate | Hard | Strenuous
                "type": "",           # Out & Back | Loop | Point to Point
                "stats": {
                    "distance": None,  # miles
                    "gain": None,      # feet
                    "time": None,      # hours round trip
                    "difficulty": ""
                },
                "parking_info": "",
                "parking_details": {
                    "fee": "",
                    "location": "",
                    "coords": [None, None]
                },
                "tags": [],
                "geo": {
                    "markers": {"start": [None, None], "summit": [None, None]},
                    "path": [],        # supply a real .gpx and run gpx-to-geo.py
                    "chart": []
                },
                "features": []
            }
        ],
        "generated_description": "",
        "nearby_peaks": [],            # pipeline can fill this once lat/lon are set
        "page_content": {
            "faqs": [],
            "seasonal_guide": [],
            "safety": {"warnings": [], "emergency": ""}
        },
        "seo": {},                     # pipeline fills this once the facts are in
        "data_sources": ds
    }


def main():
    args = sys.argv[1:]
    name = None
    if "--name" in args:
        i = args.index("--name")
        name = args[i + 1]
        args = args[:i] + args[i + 2:]
    if len(args) != 2:
        print("Usage: python3 scripts/new-trail.py <state-slug> <trail-slug> "
              "[--name \"Display Name\"]")
        sys.exit(1)

    state_slug, trail_slug = args
    _, data_sources = state_meta(state_slug)

    out_dir = DATA / state_slug
    out_file = out_dir / f"{trail_slug}.json"
    if out_file.exists():
        sys.exit(f"❌ Already exists: {out_file.relative_to(ROOT)} (refusing to overwrite)")

    out_dir.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(stub(state_slug, trail_slug, name, data_sources),
                                   indent=2) + "\n")

    print(f"✅ Created {out_file.relative_to(ROOT)}")
    print("   Next:")
    print("   1. Fill name, lat, lon, elevation, trails[].stats from an official source")
    print("   2. (optional) drop a real GPX at "
          f"gpx-downloads/{trail_slug}.gpx and set generate_gps:true")
    print(f"   3. Enable '{state_slug}' in pipeline.config.json, then run:")
    print(f"      python3 scripts/run-pipeline.py --state {state_slug}")


if __name__ == "__main__":
    main()
