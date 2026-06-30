#!/usr/bin/env python3
"""
Fetch real trail routes for draft trails from public-domain US government data.

For each draft trail (no GPS route yet) this queries the USFS National Forest
System Trails service — public domain, no key — for trail centerlines near the
summit, picks the best match (a trail whose name matches the peak, else the
nearest), assembles its segments in milepost order into a route, fills elevation
from the Open-Meteo DEM, and writes the path + distance + gain.

It does NOT auto-publish. The trail stays a draft (keeps `_status`); the quality
gate in `curate-state.py <state>` then decides — a confident name match with
good GPS density passes and goes live, a weak/sparse one stays held for review.
This keeps trust: only real, vetted routes reach the site.

Usage:
  python3 scripts/fetch-trails.py virginia
  python3 scripts/fetch-trails.py virginia --radius-km 4 --limit 10
"""

import importlib.util
import json
import math
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
USFS = ("https://apps.fs.usda.gov/arcx/rest/services/EDW/"
        "EDW_TrailNFSPublish_01/MapServer/0/query")

# Reuse Open-Meteo elevation + chart from enrich-elevation.py.
_spec = importlib.util.spec_from_file_location("ee", ROOT / "scripts" / "enrich-elevation.py")
_ee = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ee)


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


def query_usfs(lat, lon, radius_km, ctx):
    dlat = radius_km / 111.0
    dlon = radius_km / (111.0 * max(0.2, math.cos(math.radians(lat))))
    bbox = f"{lon - dlon},{lat - dlat},{lon + dlon},{lat + dlat}"
    params = {
        "geometry": bbox, "geometryType": "esriGeometryEnvelope",
        "inSR": "4326", "outSR": "4326",
        "spatialRel": "esriSpatialRelIntersects", "where": "1=1",
        "outFields": "trail_name,bmp", "returnGeometry": "true", "f": "geojson",
    }
    url = f"{USFS}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "summitseeker/1.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
                return json.loads(resp.read()).get("features", [])
        except urllib.error.URLError as e:
            if "CERTIFICATE_VERIFY_FAILED" in str(e):
                sys.exit("❌ TLS cert verification failed (macOS/python.org). Fix:\n"
                         "   /Applications/Python\\ 3.13/Install\\ Certificates.command")
            time.sleep(2 ** attempt)
        except Exception:
            time.sleep(2 ** attempt)
    return []


def coords_of(feat):
    g = feat.get("geometry") or {}
    if g.get("type") == "LineString":
        return [g["coordinates"]]
    if g.get("type") == "MultiLineString":
        return g["coordinates"]
    return []


def norm(s):
    s = (s or "").lower()
    for w in ("mount ", "mt ", "mountain", "peak", "trail"):
        s = s.replace(w, " ")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def assemble(features):
    """Order a trail's segments by milepost, return a [lat,lon] path."""
    feats = sorted(features, key=lambda f: f["properties"].get("bmp") or 0)
    path = []
    for f in feats:
        for line in coords_of(f):
            for lon, lat in line:           # GeoJSON is [lon,lat]
                p = [round(lat, 5), round(lon, 5)]
                if not path or path[-1] != p:
                    path.append(p)
    return path


def simplify(path, maxn=120):
    if len(path) <= maxn:
        return path
    step = len(path) / maxn
    out = [path[int(i * step)] for i in range(maxn)]
    if out[-1] != path[-1]:
        out.append(path[-1])
    return out


def pick_trail(features, peak_name, summit, radius_mi):
    """Group by trail_name; choose name match, else nearest within radius."""
    groups = {}
    for f in features:
        n = f["properties"].get("trail_name") or "Unnamed"
        groups.setdefault(n, []).append(f)

    peak = norm(peak_name)
    scored = []
    for name, feats in groups.items():
        path = assemble(feats)
        if len(path) < 2:
            continue
        near = min(haversine_mi(summit, p) for p in path)
        if near > radius_mi:
            continue
        tn = norm(name)
        name_match = bool(peak) and (peak in tn or tn in peak
                                     or bool(set(peak.split()) & set(tn.split())))
        scored.append((name_match, -near, name, path))
    if not scored:
        return None, None, False
    scored.sort(reverse=True)  # name match first, then nearest
    name_match, _, name, path = scored[0]
    return name, path, name_match


def orient_to_summit(path, summit):
    """Make the summit-end last so the 'summit' marker is the destination."""
    if haversine_mi(path[0], summit) < haversine_mi(path[-1], summit):
        return list(reversed(path))
    return path


def process(state, slug_filter, radius_km, limit, ctx):
    files = sorted((DATA / state).glob("*.json"))
    done = 0
    for f in files:
        if limit and done >= limit:
            break
        d = json.loads(f.read_text())
        t = (d.get("trails") or [{}])[0]
        if t.get("geo", {}).get("path"):
            continue  # already has a route
        if d.get("lat") is None or d.get("lon") is None:
            continue
        if slug_filter and d.get("slug") != slug_filter:
            continue
        summit = [d["lat"], d["lon"]]
        feats = query_usfs(d["lat"], d["lon"], radius_km, ctx)
        if not feats:
            print(f"  · no USFS trails near {d['name']}")
            continue
        name, path, name_match = pick_trail(feats, d["name"], summit,
                                            radius_mi=radius_km * 0.621)
        if not path:
            print(f"  · no usable trail near {d['name']}")
            continue
        path = simplify(orient_to_summit(path, summit))
        eles = _ee.batch_elevations([(p[0], p[1]) for p in path], ctx)
        if len(eles) != len(path):
            print(f"  · elevation fetch failed for {d['name']}")
            continue
        path3 = [[p[0], p[1], round(e)] for p, e in zip(path, eles)]
        dist = sum(haversine_mi(path3[i - 1], path3[i]) for i in range(1, len(path3)))
        geo = t.setdefault("geo", {})
        geo["path"] = path3
        geo["chart"] = _ee.build_chart(path3)
        geo.setdefault("markers", {})["summit"] = [summit[0], summit[1]]
        geo["markers"]["start"] = [path3[0][0], path3[0][1]]
        stats = t.setdefault("stats", {})
        stats["distance"] = round(dist, 1)
        stats["gain"] = round(max(eles) - min(eles))
        ds = d.setdefault("data_sources", {})
        ds["gps_source"] = "USFS National Forest System Trails (public domain)"
        ds["elevation_source"] = "Open-Meteo (Copernicus 30 m DEM)"
        ds["route_verified"] = str(date.today())
        f.write_text(json.dumps(d, indent=2) + "\n")
        flag = "name-match" if name_match else "proximity"
        print(f"  ✅ {d['name']:<26} ← \"{name}\" ({flag}, {round(dist,1)}mi, "
              f"{len(path3)}pts)")
        done += 1
    return done


def main():
    args = sys.argv[1:]
    radius_km, limit, slug = 4.0, None, None
    pos = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--radius-km":
            radius_km = float(args[i + 1]); i += 2
        elif a == "--limit":
            limit = int(args[i + 1]); i += 2
        elif a == "--slug":
            slug = args[i + 1]; i += 2
        else:
            pos.append(a); i += 1
    if not pos:
        sys.exit("Usage: python3 scripts/fetch-trails.py <state> "
                 "[--radius-km 4] [--limit N] [--slug <slug>]")
    state = pos[0]
    if not (DATA / state).is_dir():
        sys.exit(f"❌ No data folder for '{state}'")

    print(f"Fetching USFS trail routes for drafts in {state} "
          f"(radius {radius_km} km)…")
    ctx = ssl_context()
    n = process(state, slug, radius_km, limit, ctx)
    print(f"\nAttached routes to {n} trail(s). Now run:")
    print(f"  python3 scripts/run-pipeline.py --state {state}")
    print(f"  python3 scripts/curate-state.py {state}   # publishes the ones that pass quality")


if __name__ == "__main__":
    main()
