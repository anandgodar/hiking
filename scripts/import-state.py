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
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "website" / "src" / "data"
OVERPASS = "https://overpass-api.de/api/interpreter"


def ssl_context():
    """Build a verifying SSL context, preferring certifi if it's installed.

    Fixes the common macOS python.org issue where Python doesn't use the
    system keychain and TLS verification fails with CERTIFICATE_VERIFY_FAILED.
    """
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


CERT_HINT = (
    "TLS certificate verification failed. This is a macOS/python.org Python\n"
    "  issue, not an Overpass problem. Fix it once with either:\n"
    "    /Applications/Python\\ 3.13/Install\\ Certificates.command\n"
    "  or:\n"
    "    pip3 install --upgrade certifi\n"
    "  then re-run this command."
)

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

# Highest point in the United States. Nothing on land here exceeds this, so a
# computed elevation above it is proof of a unit error, never a real peak.
US_MAX_ELEVATION_FT = 20310

# US state bounding boxes (min_lat, min_lon, max_lat, max_lon), generous
# buffers included. Overpass area lookups match on NAME, and several US state
# names also name foreign admin areas — OSM has a "Florida" department in
# Uruguay, which imported 10 South American peaks into data/florida/. Any node
# outside its state's box is rejected at write time.
STATE_BBOX = {
    "alabama": (30.1, -88.6, 35.1, -84.8), "alaska": (51.0, -180.0, 71.6, -129.0),
    "arizona": (31.2, -115.0, 37.1, -108.9), "arkansas": (32.9, -94.7, 36.6, -89.6),
    "california": (32.4, -124.5, 42.1, -114.1), "colorado": (36.9, -109.1, 41.1, -102.0),
    "connecticut": (40.9, -73.8, 42.1, -71.7), "delaware": (38.4, -75.8, 39.9, -74.9),
    "florida": (24.4, -87.7, 31.1, -79.9), "georgia": (30.3, -85.7, 35.1, -80.8),
    "hawaii": (18.8, -160.3, 22.3, -154.7), "idaho": (41.9, -117.3, 49.1, -110.9),
    "illinois": (36.9, -91.6, 42.6, -87.4), "indiana": (37.7, -88.2, 41.8, -84.7),
    "iowa": (40.3, -96.7, 43.6, -90.1), "kansas": (36.9, -102.1, 40.1, -94.5),
    "kentucky": (36.4, -89.7, 39.2, -81.9), "louisiana": (28.8, -94.1, 33.1, -88.7),
    "maine": (42.9, -71.2, 47.6, -66.9), "maryland": (37.8, -79.6, 39.8, -74.9),
    "massachusetts": (41.1, -73.6, 42.9, -69.8), "michigan": (41.6, -90.5, 48.4, -82.3),
    "minnesota": (43.4, -97.3, 49.5, -89.4), "mississippi": (30.1, -91.7, 35.1, -88.0),
    "missouri": (35.9, -95.9, 40.7, -89.0), "montana": (44.3, -116.1, 49.1, -104.0),
    "nebraska": (39.9, -104.1, 43.1, -95.2), "nevada": (34.9, -120.1, 42.1, -114.0),
    "new-hampshire": (42.6, -72.6, 45.4, -70.6), "new-jersey": (38.8, -75.6, 41.4, -73.8),
    "new-mexico": (31.2, -109.1, 37.1, -102.9), "new-york": (40.4, -79.8, 45.1, -71.8),
    "north-carolina": (33.7, -84.4, 36.7, -75.4), "north-dakota": (45.8, -104.1, 49.1, -96.5),
    "ohio": (38.3, -84.9, 42.4, -80.4), "oklahoma": (33.5, -103.1, 37.1, -94.4),
    "oregon": (41.9, -124.7, 46.4, -116.4), "pennsylvania": (39.6, -80.6, 42.4, -74.6),
    "rhode-island": (41.0, -71.9, 42.1, -71.0), "south-carolina": (32.0, -83.4, 35.3, -78.4),
    "south-dakota": (42.4, -104.1, 46.0, -96.4), "tennessee": (34.9, -90.4, 36.7, -81.6),
    "texas": (25.7, -106.7, 36.6, -93.4), "utah": (36.9, -114.1, 42.1, -108.9),
    "vermont": (42.6, -73.5, 45.1, -71.4), "virginia": (36.4, -83.7, 39.5, -75.1),
    "washington": (45.4, -124.9, 49.1, -116.8), "west-virginia": (37.1, -82.7, 40.7, -77.6),
    "wisconsin": (42.4, -92.9, 47.4, -86.2), "wyoming": (40.9, -111.1, 45.1, -104.0),
}


def _load_sibling(name):
    """Import a hyphenated sibling script as a module."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        name.replace("-", "_"), Path(__file__).resolve().parent / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def in_state_bounds(state_slug, lat, lon):
    box = STATE_BBOX.get(state_slug)
    if not box or lat is None or lon is None:
        return True  # unknown state: don't silently drop
    min_lat, min_lon, max_lat, max_lon = box
    return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon


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
    ctx = ssl_context()
    last = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=180, context=ctx) as resp:
                return json.loads(resp.read())
        except urllib.error.URLError as e:
            # Certificate failures will never succeed on retry — fail fast with
            # an actionable hint instead of burning the retry budget.
            if isinstance(getattr(e, "reason", None), ssl.SSLCertVerificationError) \
                    or "CERTIFICATE_VERIFY_FAILED" in str(e):
                sys.exit(f"❌ {CERT_HINT}")
            last = e
            wait = 2 ** attempt * 3
            print(f"  · Overpass unreachable ({e}); retrying in {wait}s "
                  f"[{attempt + 1}/{retries}]")
            time.sleep(wait)
        except Exception as e:  # 429/504/timeouts are common on the public server
            last = e
            wait = 2 ** attempt * 3
            print(f"  · Overpass busy ({e}); retrying in {wait}s "
                  f"[{attempt + 1}/{retries}]")
            time.sleep(wait)
    raise last


def parse_ele(tags, dem_ft=None):
    """Resolve an OSM `ele` tag to feet, cross-checked against the DEM.

    OSM specifies `ele` in metres, but US contributors frequently tag the
    value in feet. Blindly multiplying by 3.28084 turned Mother Lode Peak's
    correct 7,908 ft into 25,945 ft. So: interpret the raw number BOTH ways
    and keep whichever matches the Copernicus DEM sample for the same
    coordinate.

    This only ever REJECTS a reading, never rewrites an elevation to a DEM
    value — a 30 m point sample is not a summit benchmark, and a previous
    attempt to auto-correct elevations that way corrupted good records
    (Mt Carrigain 4,700 -> 4,545). If neither reading is credible we return
    None and the caller holds the peak as a draft rather than guessing.
    """
    raw = tags.get("ele")
    if not raw:
        return None
    m = re.match(r"[-+]?[0-9]*\.?[0-9]+", str(raw).replace(",", "."))
    if not m:
        return None
    value = float(m.group())
    as_metres = round(value * M_TO_FT)   # per OSM spec
    as_feet = round(value)               # common US mis-tagging

    if dem_ft is None:
        # No DEM available: keep the spec reading, but never emit a value that
        # is physically impossible in the US.
        return None if as_metres > US_MAX_ELEVATION_FT else as_metres

    tolerance = max(150.0, dem_ft * 0.10)
    candidates = [(abs(as_metres - dem_ft), as_metres), (abs(as_feet - dem_ft), as_feet)]
    delta, best = min(candidates)
    if delta > tolerance or best <= 0 or best > US_MAX_ELEVATION_FT:
        return None  # not credible against the DEM — caller must hold as draft
    return best


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

    # Reject nodes outside the state's real geography. Overpass matches areas
    # by name, and several US state names also name foreign admin areas.
    in_bounds, out_of_bounds = [], 0
    for el in elements:
        if in_state_bounds(state_slug, el.get("lat"), el.get("lon")):
            in_bounds.append(el)
        else:
            out_of_bounds += 1
    if out_of_bounds:
        print(f"  ⚠ rejected {out_of_bounds} node(s) outside {state_name}'s "
              f"bounding box (foreign area name collision)")
    elements = in_bounds

    # Batch-fetch DEM elevations so `ele` tags can be unit-checked (see
    # parse_ele). One batched call, not one per peak.
    dem = {}
    try:
        _ee = _load_sibling("enrich-elevation")
        coords = [(el["lat"], el["lon"]) for el in elements]
        values = _ee.batch_elevations(coords, ssl_context()) if coords else []
        if len(values) == len(elements):
            dem = {el["id"]: v for el, v in zip(elements, values)}
        else:
            print("  ⚠ DEM sample incomplete — elevations fall back to spec reading")
    except Exception as e:
        print(f"  ⚠ DEM unavailable ({e}) — elevations fall back to spec reading")

    # Filter
    kept = []
    unverified = 0
    for el in elements:
        tags = el["tags"]
        elev = parse_ele(tags, dem.get(el["id"]))
        if elev is None:
            unverified += 1
            continue
        if elev < opts["min_ele"]:
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
    if unverified:
        print(f"  ⚠ {unverified} peak(s) skipped: elevation could not be verified "
              f"against the DEM in either metres or feet")

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
