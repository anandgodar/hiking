#!/usr/bin/env python3
"""
Fully automated: build a whole state's trails with one command.

Runs the entire pipeline end to end for a state, using only real public-domain /
ODbL data, and auto-publishes the trails that pass the quality gate:

  1. import-state      peaks from OpenStreetMap (name, coords, elevation)
  2. curate prune      drop the OSM noise, keep notable destinations
  3. fetch-trails      real routes from USFS / NPS / USGS National Map
  4. enrich-elevation  fill elevation on any 2-D path (Open-Meteo DEM)
  5. enrich-poi        trailhead, parking, and along-trail features (OSM)
  6. run-pipeline      nearby peaks, descriptions, SEO, link check, audit, validate
  7. curate publish    auto-publish every trail that meets the quality bar
  8. enable the state in pipeline.config.json + report LIVE vs DRAFT

Nothing is fabricated; trails that lack a real route stay draft (hidden). This
is network-heavy (OSM + government services) — expect a few minutes per state.

Usage:
  python3 scripts/auto-state.py colorado
  python3 scripts/auto-state.py virginia --min-ele 2000 --keep-top 25 --radius-km 5
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def run(label, cmd):
    print(f"\n{'─' * 70}\n▶ {label}\n{'─' * 70}")
    r = subprocess.run(cmd)
    if r.returncode != 0:
        print(f"  ⚠️  {label} exited {r.returncode} (continuing)")
    return r.returncode


def enable_state(slug):
    cfg = ROOT / "pipeline.config.json"
    d = json.loads(cfg.read_text())
    for s in d.get("states", []):
        if s["slug"] == slug and not s.get("enabled"):
            s["enabled"] = True
            cfg.write_text(json.dumps(d, indent=2) + "\n")
            return True
    return False


def main():
    p = argparse.ArgumentParser(description="Fully automated state build")
    p.add_argument("state")
    p.add_argument("--min-ele", type=int, default=None,
                   help="skip peaks below this elevation (ft); "
                        "default from pipeline.config.json per-state tuning")
    p.add_argument("--max-ele", type=int, default=None,
                   help="skip peaks above this elevation (ft); default from "
                        "pipeline.config.json per-state tuning, unset by default")
    p.add_argument("--sort-by", choices=["elevation", "prominence"], default=None,
                   help="rank candidates by tallest (default) or most "
                        "prominent/standalone within the elevation band; "
                        "default from pipeline.config.json per-state tuning")
    p.add_argument("--keep-top", type=int, default=None,
                   help="keep the N most notable peaks after import")
    p.add_argument("--near-population", type=float, default=None,
                   help="restrict candidates to within N miles of a real "
                        "population center before ranking (see "
                        "POPULATION_CENTERS in curate-state.py); default "
                        "from pipeline.config.json per-state tuning")
    p.add_argument("--ignore-elevation-ranking", action="store_true",
                   help="rank prune candidates by prominence/wikidata only, "
                        "not raw elevation; default from pipeline.config.json")
    p.add_argument("--radius-km", type=float, default=4.0,
                   help="search radius for routes/POIs")
    p.add_argument("--skip-import", action="store_true",
                   help="use existing data; don't re-import from OSM")
    args = p.parse_args()
    s = args.state
    py = sys.executable

    # Per-state import tuning from the config (state highpoints differ wildly:
    # Colorado's floor is 5000 ft, Florida's is 0). CLI flags override.
    cfg = json.loads((ROOT / "pipeline.config.json").read_text())
    tuning = next((st.get("import", {}) for st in cfg.get("states", [])
                   if st["slug"] == s), {})
    if args.min_ele is None:
        args.min_ele = tuning.get("min_ele", 2000)
    if args.max_ele is None:
        args.max_ele = tuning.get("max_ele")
    if args.sort_by is None:
        args.sort_by = tuning.get("sort_by", "elevation")
    if args.keep_top is None:
        args.keep_top = tuning.get("keep_top", 25)
    if args.near_population is None:
        args.near_population = tuning.get("near_population_mi")
    if not args.ignore_elevation_ranking:
        args.ignore_elevation_ranking = tuning.get("ignore_elevation_ranking", False)

    max_desc = f" · max-ele {args.max_ele}ft" if args.max_ele else ""
    print(f"╔{'═' * 68}╗")
    print(f"  FULLY AUTOMATED BUILD · {s} · min-ele {args.min_ele}ft{max_desc} · "
          f"sort-by {args.sort_by} · keep-top {args.keep_top}")
    print(f"╚{'═' * 68}╝")

    if not args.skip_import:
        import_cmd = [py, str(SCRIPTS / "import-state.py"), s,
                      "--min-ele", str(args.min_ele), "--sort-by", args.sort_by]
        if args.max_ele:
            import_cmd += ["--max-ele", str(args.max_ele)]
        run("1/7  Import peaks (OpenStreetMap)", import_cmd)
        prune_cmd = [py, str(SCRIPTS / "curate-state.py"), s, "prune",
                     "--keep-top", str(args.keep_top), "--apply"]
        if args.near_population:
            prune_cmd += ["--near-population", str(args.near_population)]
        if args.ignore_elevation_ranking:
            prune_cmd += ["--ignore-elevation"]
        run("2/7  Prune to notable destinations", prune_cmd)

    run("3/7  Fetch real routes (USFS / NPS / USGS)",
        [py, str(SCRIPTS / "fetch-trails.py"), s, "--radius-km", str(args.radius_km)])
    run("4/7  Fill elevation on 2-D paths (Open-Meteo)",
        [py, str(SCRIPTS / "enrich-elevation.py"), "--state", s])
    run("5/7  Trailhead, parking & features (OpenStreetMap)",
        [py, str(SCRIPTS / "enrich-poi.py"), s])
    run("6/7  Enrich + audit + validate",
        [py, str(SCRIPTS / "run-pipeline.py"), "--state", s])
    run("7/7  Publish everything that passes quality",
        [py, str(SCRIPTS / "curate-state.py"), s])

    if enable_state(s):
        print(f"\n  · enabled '{s}' in pipeline.config.json")

    print(f"\n{'═' * 70}\nFINAL STATUS\n{'═' * 70}")
    subprocess.run([py, str(SCRIPTS / "draft-status.py"), s])
    print("\n✅ Done. Build the site to see it live:")
    print("   cd website && npm run build      (or: SHOW_DRAFTS=1 npm run dev to see drafts)")


if __name__ == "__main__":
    main()
