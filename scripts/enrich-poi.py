#!/usr/bin/env python3
"""
Enrich trails with a real trailhead, parking, and along-trail features (OSM).

A hike should start at a trailhead, not just "the first GPS point", and the page
is far more useful when it marks what you pass — waterfalls, overlooks, shelters,
boulders, cliffs, rest areas. This queries OpenStreetMap (Overpass, ODbL) around
each trail's route and fills:

  * geo.markers.start  → nearest trailhead (highway=trailhead), else parking
  * parking_info / parking_details → nearest parking lot (name + coords + fee)
  * trails[].features[] → POIs within ~250 m of the route, with mile along trail

Only trails that already have a GPS route are processed (run fetch-trails.py or
add a GPX first). Everything is real OSM data; nothing is invented.

Usage:
  python3 scripts/enrich-poi.py virginia
  python3 scripts/enrich-poi.py virginia --slug mount-rogers-va
"""

import json
import math
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "website" / "src" / "data"
OVERPASS = "https://overpass-api.de/api/interpreter"

# OSM tag → our feature type. Order matters (first match wins).
FEATURE_TAGS = [
    ('natural', 'waterfall', 'waterfall'),
    ('waterway', 'waterfall', 'waterfall'),
    ('tourism', 'viewpoint', 'viewpoint'),
    ('man_made', 'tower', 'fire tower'),
    ('natural', 'peak', 'summit'),
    ('amenity', 'shelter', 'hut'),
    ('tourism', 'wilderness_hut', 'hut'),
    ('tourism', 'alpine_hut', 'hut'),
    ('amenity', 'picnic_site', 'rest area'),
    ('tourism', 'picnic_site', 'rest area'),
    ('amenity', 'bench', 'rest area'),
    ('natural', 'cliff', 'cliff'),
    ('climbing', 'crag', 'cliff'),
    ('natural', 'rock', 'boulder'),
    ('natural', 'stone', 'boulder'),
    ('natural', 'cave_entrance', 'cave'),
    ('natural', 'spring', 'spring'),
    ('natural', 'arch', 'arch'),
]


def ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def haversine_mi(a, b):
    R = 3959
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dlat = math.radians(b[0] - a[0]); dlon = math.radians(b[1] - a[1])
    h = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(h))


def overpass(query, ctx):
    data = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(OVERPASS, data=data,
                                 headers={"User-Agent": "summitseeker/1.0"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
                return json.loads(resp.read()).get("elements", [])
        except urllib.error.URLError as e:
            if "CERTIFICATE_VERIFY_FAILED" in str(e):
                sys.exit("❌ TLS cert verification failed (macOS/python.org). Fix:\n"
                         "   /Applications/Python\\ 3.13/Install\\ Certificates.command")
            time.sleep(2 ** attempt * 2)
        except Exception:
            time.sleep(2 ** attempt * 2)
    return []


def bbox_of(path, pad=0.01):
    lats = [p[0] for p in path]; lons = [p[1] for p in path]
    return (min(lats) - pad, min(lons) - pad, max(lats) + pad, max(lons) + pad)


def feature_type(tags):
    for k, v, label in FEATURE_TAGS:
        if tags.get(k) == v:
            return label
    return None


def nearest_mile(path, cum, pt):
    """Distance along the trail (miles) to the path point nearest pt."""
    best_i = min(range(len(path)), key=lambda i: haversine_mi(path[i], pt))
    off = haversine_mi(path[best_i], pt)
    return round(cum[best_i], 2), off


def process_trail(d, ctx, max_off_mi=0.2):
    t = (d.get("trails") or [{}])[0]
    path = [[p[0], p[1]] for p in (t.get("geo", {}).get("path") or [])]
    if len(path) < 2:
        return False
    s, w, n, e = bbox_of(path)
    # cumulative distance along path
    cum = [0.0]
    for i in range(1, len(path)):
        cum.append(cum[-1] + haversine_mi(path[i - 1], path[i]))

    q = (f"[out:json][timeout:90];("
         f'node["highway"="trailhead"]({s},{w},{n},{e});'
         f'node["amenity"="parking"]({s},{w},{n},{e});'
         f'node["natural"="waterfall"]({s},{w},{n},{e});'
         f'node["waterway"="waterfall"]({s},{w},{n},{e});'
         f'node["tourism"="viewpoint"]({s},{w},{n},{e});'
         f'node["man_made"="tower"]["tower:type"="observation"]({s},{w},{n},{e});'
         f'node["amenity"~"shelter|picnic_site|bench"]({s},{w},{n},{e});'
         f'node["tourism"~"wilderness_hut|alpine_hut|picnic_site"]({s},{w},{n},{e});'
         f'node["natural"~"cliff|rock|stone|cave_entrance|spring|arch|peak"]({s},{w},{n},{e});'
         f");out;")
    els = overpass(q, ctx)
    if not els:
        return False

    start_pt = path[0]
    trailheads, parkings, features = [], [], []
    for el in els:
        if "lat" not in el:
            continue
        pt = [el["lat"], el["lon"]]
        tags = el.get("tags", {})
        if tags.get("highway") == "trailhead":
            trailheads.append((haversine_mi(start_pt, pt), pt, tags))
        elif tags.get("amenity") == "parking":
            parkings.append((haversine_mi(start_pt, pt), pt, tags))
        else:
            ftype = feature_type(tags)
            if not ftype:
                continue
            mile, off = nearest_mile(path, cum, pt)
            if off <= max_off_mi and tags.get("name"):
                features.append({"name": tags["name"], "type": ftype,
                                 "lat": round(pt[0], 5), "lon": round(pt[1], 5),
                                 "mile": mile})

    geo = t.setdefault("geo", {}); markers = geo.setdefault("markers", {})
    changed = []

    # Start marker: prefer a trailhead, else nearest parking, within ~1 mi of start.
    th = sorted(trailheads)[:1]
    pk = sorted(parkings)[:1]
    if th and th[0][0] < 1.0:
        markers["start"] = [round(th[0][1][0], 5), round(th[0][1][1], 5)]
        changed.append("trailhead start")
    if pk and pk[0][0] < 1.5:
        ptags = pk[0][2]
        t["parking_info"] = ptags.get("name") or t.get("parking_info") or "Trailhead parking"
        t.setdefault("parking_details", {})
        t["parking_details"]["coords"] = [round(pk[0][1][0], 5), round(pk[0][1][1], 5)]
        if ptags.get("fee"):
            t["parking_details"]["fee"] = "Yes" if ptags["fee"] == "yes" else ptags["fee"]
        changed.append("parking")

    if features:
        # de-dupe by (name,type), keep closest-to-trail, sort by mile
        uniq = {}
        for ft in sorted(features, key=lambda x: x["mile"]):
            uniq.setdefault((ft["name"], ft["type"]), ft)
        t["features"] = sorted(uniq.values(), key=lambda x: x["mile"])
        changed.append(f"{len(t['features'])} features")

    if not changed:
        return False
    ds = d.setdefault("data_sources", {})
    poi = ds.get("poi_source", "")
    ds["poi_source"] = "OpenStreetMap contributors (ODbL)"
    print(f"  ✅ {d['name']:<26} {', '.join(changed)}")
    return True


def main():
    args = sys.argv[1:]
    slug = None
    if "--slug" in args:
        i = args.index("--slug"); slug = args[i + 1]; args = args[:i] + args[i + 2:]
    if not args:
        sys.exit("Usage: python3 scripts/enrich-poi.py <state> [--slug <slug>]")
    state = args[0]
    if not (DATA / state).is_dir():
        sys.exit(f"❌ No data folder for '{state}'")

    ctx = ssl_context()
    n = 0
    for f in sorted((DATA / state).glob("*.json")):
        d = json.loads(f.read_text())
        if slug and d.get("slug") != slug:
            continue
        if not (d.get("trails") or [{}])[0].get("geo", {}).get("path"):
            continue  # needs a route first
        if process_trail(d, ctx):
            f.write_text(json.dumps(d, indent=2) + "\n")
            n += 1
        time.sleep(0.5)
    print(f"\nEnriched {n} trail(s) with trailhead / parking / features from OSM.")


if __name__ == "__main__":
    main()
