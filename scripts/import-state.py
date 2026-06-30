#!/usr/bin/env python3
"""
Import all named peaks for a state from OpenStreetMap into trail JSON files.

Give it a state; it queries the Overpass API for every named summit in that
state and writes one trail JSON per peak with the real, verifiable facts OSM
provides — name, coordinates, elevation — plus ODbL attribution. It does NOT
fabricate the facts OSM lacks (trail distance, difficulty, route geometry):
those are left blank for a real GPX (gpx-to-geo.py) or manual entry, and every
imported file is marked "imported-unverified" so validate-trail-data.js keeps
it flagged until a human confirms it against the official land manager.

After importing, run the normal pipeline to enrich (SEO, nearby_peaks) and
audit. Frontend-ready GPS still needs a real .gpx per trail.

Usage:
  python3 scripts/import-state.py <state-slug> [options]
Options:
  --min-ele FEET     skip peaks below this elevation (default 0)
  --min-prominence M skip peaks below this prominence in meters (default 0)
  --limit N          keep only the N highest peaks (default: no limit)
  --dry-run          report what would be imported, write nothing

Examples:
  python3 scripts/import-state.py colorado --min-ele 13000
  python3 scripts/import-state.py vermont --limit 50 --dry-run
"""

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "website" / "src" / "data"
OVERPASS = "https://overpass-api.de/api/interpreter"

# slug -> (official OSM name, 2-letter abbreviation)
STATES = {
    "alabama": ("Alabama", "al"), "alaska": ("Alaska", "ak"),
    "arizona": ("Arizona", "az"), "arkansas": ("Arkansas", "ar"),
    "california": ("California", "ca"), "colorado": ("Colorado", "co"),
    "connecticut": ("Connecticut", "ct"), "delaware": ("Delaware", "de"),
    "florida": ("Florida", "fl"), "georgia": ("Georgia", "ga"),
    "hawaii": ("Hawaii", "hi"), "idaho": ("Idaho", "id"),
    "illinois": ("Illinois", "il"), "indiana": ("Indiana", "in"),
    "iowa": ("Iowa", "ia"), "kansas": ("Kansas", "ks"),
    "kentucky": ("Kentucky", "ky"), "louisiana": ("Louisiana", "la"),
    "maine": ("Maine", "me"), "maryland": ("Maryland", "md"),
    "massachusetts": ("Massachusetts", "ma"), "michigan": ("Michigan", "mi"),
    "minnesota": ("Minnesota", "mn"), "mississippi": ("Mississippi", "ms"),
    "missouri": ("Missouri", "mo"), "montana": ("Montana", "mt"),
    "nebraska": ("Nebraska", "ne"), "nevada": ("Nevada", "nv"),
    "new-hampshire": ("New Hampshire", "nh"), "new-jersey": ("New Jersey", "nj"),
    "new-mexico": ("New Mexico", "nm"), "new-york": ("New York", "ny"),
    "north-carolina": ("North Carolina", "nc"), "north-dakota": ("North Dakota", "nd"),
    "ohio": ("Ohio", "oh"), "oklahoma": ("Oklahoma", "ok"),
    "oregon": ("Oregon", "or"), "pennsylvania": ("Pennsylvania", "pa"),
    "rhode-island": ("Rhode Island", "ri"), "south-carolina": ("South Carolina", "sc"),
    "south-dakota": ("South Dakota", "sd"), "tennessee": ("Tennessee", "tn"),
    "texas": ("Texas", "tx"), "utah": ("Utah", "ut"), "vermont": ("Vermont", "vt"),
    "virginia": ("Virginia", "va"), "washington": ("Washington", "wa"),
    "west-virginia": ("West Virginia", "wv"), "wisconsin": ("Wisconsin", "wi"),
    "wyoming": ("Wyoming", "wy"),
}

M_TO_FT = 3.28084


def slugify(name, abbr):
    s = name.lower()
    s = re.sub(r"[''’]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return f"{s}-{abbr}"


def overpass_query(state_name, retries=4):
    q = (f'[out:json][timeout:120];'
         f'area["name"="{state_name}"]["admin_level"="4"]["boundary"="administrative"]->.a;'
         f'node["natural"="peak"]["name"](area.a);out;')
    data = urllib.parse.urlencode({"data": q}).encode()
    req = urllib.request.Request(
        OVERPASS, data=data,
        headers={"User-Agent": "summitseeker-import/1.0 (trail data importer)"})
    last = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read())
        except Exception as e:  # 429/504/timeouts are common on the public server
            last = e
            wait = 2 ** attempt * 3
            print(f"  · Overpass busy ({e}); retrying in {wait}s "
                  f"[{attempt + 1}/{retries}]")
            time.sleep(wait)
    raise last


def parse_ele(tags):
    raw = tags.get("ele")
    if not raw:
        return None
    m = re.match(r"[-+]?[0-9]*\.?[0-9]+", str(raw).replace(",", "."))
    if not m:
        return None
    return round(float(m.group()) * M_TO_FT)  # OSM ele is metres


def config_data_sources(state_slug):
    cfg = ROOT / "pipeline.config.json"
    if cfg.exists():
        for s in json.loads(cfg.read_text()).get("states", []):
            if s["slug"] == state_slug:
                return s.get("data_sources")
    return None


def enable_state(state_slug):
    """Flip enabled:true for the state in pipeline.config.json (preserves order)."""
    cfg_path = ROOT / "pipeline.config.json"
    cfg = json.loads(cfg_path.read_text())
    for s in cfg.get("states", []):
        if s["slug"] == state_slug:
            if s.get("enabled"):
                return False
            s["enabled"] = True
            cfg_path.write_text(json.dumps(cfg, indent=2) + "\n")
            return True
    return False


def build_record(el, state_slug, state_name, abbr):
    tags = el["tags"]
    name = tags["name"]
    slug = slugify(name, abbr)
    elev_ft = parse_ele(tags)
    osm_url = f"https://www.openstreetmap.org/node/{el['id']}"

    ds = config_data_sources(state_slug) or {}
    ds = dict(ds)
    ds.update({
        "verified_by": "OpenStreetMap contributors (ODbL) — VERIFY against official source",
        "primary_url": ds.get("primary_url") or osm_url,
        "osm_node": osm_url,
        "elevation_source": "OpenStreetMap (verify vs USGS benchmark)",
        "gps_source": "OpenStreetMap",
        "verification_date": str(date.today()),
    })

    return slug, {
        "_status": "imported-unverified — confirm facts, add route distance/"
                   "difficulty and a real GPX, then remove this key",
        "name": name,
        "slug": slug,
        "state": state_name,
        "state_slug": state_slug,
        "elevation": elev_ft,
        "lat": round(el["lat"], 5),
        "lon": round(el["lon"], 5),
        "mountain_hero": "",
        "tags": [],
        "trails": [{
            "name": f"{name} Trail",
            "difficulty": "",
            "type": "",
            "stats": {"distance": None, "gain": None, "time": None, "difficulty": ""},
            "parking_info": "",
            "parking_details": {"fee": "", "location": "", "coords": [None, None]},
            "tags": [],
            "geo": {"markers": {"start": [None, None],
                                "summit": [round(el["lat"], 5), round(el["lon"], 5)]},
                    "path": [], "chart": []},
            "features": []
        }],
        "generated_description": "",
        "nearby_peaks": [],
        "page_content": {"faqs": [], "seasonal_guide": [],
                         "safety": {"warnings": [], "emergency": ""}},
        "seo": {},
        "data_sources": ds,
        "osm": {"id": el["id"],
                "prominence_m": tags.get("prominence"),
                "wikidata": tags.get("wikidata")},
    }


def main():
    args = sys.argv[1:]
    opts = {"min_ele": 0, "min_prominence": 0, "limit": None, "dry_run": False,
            "enable": False, "pipeline": False}
    positional = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--min-ele":
            opts["min_ele"] = float(args[i + 1]); i += 2
        elif a == "--min-prominence":
            opts["min_prominence"] = float(args[i + 1]); i += 2
        elif a == "--limit":
            opts["limit"] = int(args[i + 1]); i += 2
        elif a == "--dry-run":
            opts["dry_run"] = True; i += 1
        elif a == "--enable":
            opts["enable"] = True; i += 1
        elif a == "--pipeline":
            opts["pipeline"] = True; i += 1
        else:
            positional.append(a); i += 1

    if len(positional) != 1 or positional[0] not in STATES:
        print("Usage: python3 scripts/import-state.py <state-slug> [options]")
        print("Valid state slugs:", ", ".join(sorted(STATES)))
        sys.exit(1)

    state_slug = positional[0]
    state_name, abbr = STATES[state_slug]

    print(f"Querying OpenStreetMap for named peaks in {state_name}…")
    try:
        result = overpass_query(state_name)
    except Exception as e:
        sys.exit(f"❌ Overpass query failed: {e}")

    elements = [e for e in result.get("elements", []) if e.get("tags", {}).get("name")]
    print(f"  {len(elements)} named peaks returned")

    # Filter
    kept = []
    for el in elements:
        tags = el["tags"]
        elev = parse_ele(tags)
        if elev is None or elev < opts["min_ele"]:
            continue
        prom = tags.get("prominence")
        if opts["min_prominence"] and (not prom or float(re.match(r"[-+]?[0-9.]+", str(prom)).group()) < opts["min_prominence"]):
            continue
        kept.append((elev, el))

    kept.sort(key=lambda x: x[0], reverse=True)
    if opts["limit"]:
        kept = kept[:opts["limit"]]

    print(f"  {len(kept)} peaks after filters "
          f"(min_ele={opts['min_ele']}ft, min_prom={opts['min_prominence']}m, "
          f"limit={opts['limit']})")

    out_dir = DATA / state_slug
    written = skipped = 0
    seen = set()
    for elev, el in kept:
        slug, record = build_record(el, state_slug, state_name, abbr)
        if slug in seen:
            continue
        seen.add(slug)
        out_file = out_dir / f"{slug}.json"
        if out_file.exists():
            skipped += 1
            continue
        if opts["dry_run"]:
            print(f"    would write {slug}.json  ({elev} ft)")
            continue
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file.write_text(json.dumps(record, indent=2) + "\n")
        written += 1

    if opts["dry_run"]:
        print(f"\nDry run: {len(kept)} peaks would be considered "
              f"({skipped} already exist).")
        return

    print(f"\n✅ Wrote {written} trail file(s) to website/src/data/{state_slug}/ "
          f"({skipped} already existed).")

    if opts["enable"]:
        if enable_state(state_slug):
            print(f"   · enabled '{state_slug}' in pipeline.config.json")
        else:
            print(f"   · '{state_slug}' already enabled in pipeline.config.json")

    if opts["pipeline"]:
        print(f"\n▶ Running pipeline for {state_slug}…\n")
        import subprocess
        subprocess.run([sys.executable, str(ROOT / "scripts" / "run-pipeline.py"),
                        "--state", state_slug])

    print("\n   Finish each trail: add route distance/difficulty + a real GPX, "
          "verify facts against the official land manager, then drop the "
          "_status key.")
    if not opts["pipeline"]:
        nxt = "" if opts["enable"] else \
            f"   1. Enable '{state_slug}' in pipeline.config.json\n"
        print("   Next:")
        if nxt:
            print(nxt, end="")
        print(f"   {'1' if opts['enable'] else '2'}. "
              f"python3 scripts/run-pipeline.py --state {state_slug}")


if __name__ == "__main__":
    main()
