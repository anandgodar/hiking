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

# Public-domain route sources, tried in order. Each: (label, query-url,
# name-field, order-field-or-None, attribution).
SOURCES = [
    ("USFS",
     "https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_TrailNFSPublish_01/MapServer/0/query",
     "trail_name", "bmp",
     "USFS National Forest System Trails (public domain)"),
    ("NPS",
     "https://mapservices.nps.gov/arcgis/rest/services/NationalDatasets/NPS_Public_Trails/MapServer/0/query",
     "TRLNAME", None,
     "National Park Service Public Trails (public domain)"),
    ("USGS",
     "https://carto.nationalmap.gov/arcgis/rest/services/transportation/MapServer/37/query",
     "name", None,
     "USGS National Map / National Transportation Dataset (public domain)"),
]


def load_extra_sources():
    """Append custom ArcGIS REST trail services from trail-sources.json, e.g.
    state-park GIS portals. Each entry: {label,url,name_field,order_field,attribution}.
    Lets you extend coverage (state/county data) without editing this script."""
    cfg = ROOT / "trail-sources.json"
    if not cfg.exists():
        return
    try:
        for s in json.loads(cfg.read_text()):
            SOURCES.append((s["label"], s["url"], s["name_field"],
                            s.get("order_field"), s.get("attribution", s["label"])))
    except Exception as e:
        print(f"  · ignoring trail-sources.json ({e})")

# Reuse Open-Meteo elevation + chart from enrich-elevation.py.
_spec = importlib.util.spec_from_file_location("ee", ROOT / "scripts" / "enrich-elevation.py")
_ee = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ee)

# Canonical distance semantics (route_length_mi / distance_type / distance).
sys.path.insert(0, str(ROOT / "scripts"))
import route_metrics as _rm  # noqa: E402


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


def query_source(url, name_field, order_field, lat, lon, radius_km, ctx,
                 name_eq=None):
    """Query one ArcGIS REST trail service; return normalized features:
    {name, order, lines:[[ [lon,lat],... ]]}.

    With name_eq, filters to one exact trail name — used to fetch the FULL
    geometry of a matched trail with a wide bbox, since the small discovery
    bbox clips long approach trails (Barr Trail is 13 mi; a 4 km box keeps
    only the summit fragment).
    """
    dlat = radius_km / 111.0
    dlon = radius_km / (111.0 * max(0.2, math.cos(math.radians(lat))))
    bbox = f"{lon - dlon},{lat - dlat},{lon + dlon},{lat + dlat}"
    out_fields = name_field + ("," + order_field if order_field else "")
    where = "1=1"
    if name_eq:
        # Services often split one trail into suffix-named segments
        # ("North Longs Peak - Upper" / "- Lower"). Match on the base name so
        # all segments return; the stitcher keeps the connected chain.
        base = re.sub(r"\s*[-–]\s*[A-Za-z0-9 ]{1,12}$", "", name_eq).strip() or name_eq
        safe = base.replace(chr(39), chr(39) * 2)
        where = f"{name_field} LIKE '{safe}%'"
    params = {
        "geometry": bbox, "geometryType": "esriGeometryEnvelope",
        "inSR": "4326", "outSR": "4326",
        "spatialRel": "esriSpatialRelIntersects", "where": where,
        "outFields": out_fields, "returnGeometry": "true", "f": "geojson",
    }
    full = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(full, headers={"User-Agent": "summitseeker/1.0"})
    feats = []
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
                feats = json.loads(resp.read()).get("features", [])
            break
        except urllib.error.URLError as e:
            if "CERTIFICATE_VERIFY_FAILED" in str(e):
                sys.exit("❌ TLS cert verification failed (macOS/python.org). Fix:\n"
                         "   /Applications/Python\\ 3.13/Install\\ Certificates.command")
            time.sleep(2 ** attempt)
        except Exception:
            time.sleep(2 ** attempt)
    norm_feats = []
    for ft in feats:
        props = ft.get("properties") or {}
        norm_feats.append({
            "name": props.get(name_field) or "Unnamed",
            "order": (props.get(order_field) or 0) if order_field else 0,
            "lines": coords_of(ft),
        })
    return norm_feats


OVERPASS = "https://overpass-api.de/api/interpreter"


def query_osm_paths(lat, lon, radius_km, ctx):
    """Last-resort source: NAMED hiking ways from OpenStreetMap (ODbL).

    State parks and local trails are often absent from the federal services
    but well-mapped in OSM. Only named path/footway/track ways are used —
    unnamed social trails are noise. Same normalized shape as query_source.
    """
    r = int(radius_km * 1000)
    q = (f'[out:json][timeout:60];way["name"]'
         f'["highway"~"^(path|footway|track)$"](around:{r},{lat},{lon});'
         f'out geom;')
    data = urllib.parse.urlencode({"data": q}).encode()
    req = urllib.request.Request(
        OVERPASS, data=data,
        headers={"User-Agent": "summitseeker/1.0 (trail fetcher)"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90, context=ctx) as resp:
                els = json.loads(resp.read()).get("elements", [])
            break
        except Exception:
            time.sleep(3 * (attempt + 1))
    else:
        return []
    feats = []
    for el in els:
        geom = el.get("geometry") or []
        if len(geom) < 2:
            continue
        feats.append({
            "name": el.get("tags", {}).get("name", "Unnamed"),
            "order": 0,
            "lines": [[[g["lon"], g["lat"]] for g in geom]],
        })
    return feats


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


JOIN_GAP_MI = 0.12  # segments whose endpoints are farther apart than this
                    # are disconnected pieces, not a continuation


def assemble(features):
    """Stitch a trail's segments into one CONTINUOUS [lat,lon] path.

    GIS services return a trail as many independent polylines, often disjoint
    (parallel spurs, far-apart pieces sharing a name). Naively concatenating
    them draws long straight jumps across the map. Instead: greedy endpoint
    chaining — start from the longest segment, repeatedly attach the segment
    whose nearest endpoint is within JOIN_GAP_MI of the chain's ends (reversing
    as needed), and DROP anything that doesn't connect. The result is the
    longest continuous run, which is what a hiker actually walks.
    """
    segs = []
    for f in sorted(features, key=lambda f: f.get("order") or 0):
        for line in f.get("lines", []):
            pts = [[round(lat, 5), round(lon, 5)] for lon, lat in line]
            if len(pts) >= 2:
                segs.append(pts)
    if not segs:
        return []

    def seg_len(s):
        return sum(haversine_mi(s[i - 1], s[i]) for i in range(1, len(s)))

    segs.sort(key=seg_len, reverse=True)
    chain = list(segs.pop(0))

    attached = True
    while attached and segs:
        attached = False
        best = None  # (gap, idx, at_start, reverse)
        for i, s in enumerate(segs):
            for at_start in (False, True):
                end = chain[0] if at_start else chain[-1]
                for rev in (False, True):
                    tip = (s[-1] if rev else s[0]) if not at_start else \
                          (s[0] if rev else s[-1])
                    gap = haversine_mi(end, tip)
                    if gap <= JOIN_GAP_MI and (best is None or gap < best[0]):
                        best = (gap, i, at_start, rev)
        if best:
            _, i, at_start, rev = best
            s = segs.pop(i)
            if rev:
                s = list(reversed(s))
            if at_start:
                chain = s + chain
            else:
                chain = chain + s
            attached = True

    # de-dup consecutive identical points
    path = [chain[0]]
    for p in chain[1:]:
        if p != path[-1]:
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


def path_len_mi(path):
    return sum(haversine_mi(path[i - 1], path[i]) for i in range(1, len(path)))


# A proximity (non-name) match must look like a real day hike. Too short = a
# tiny unrelated feature (e.g. a 0.1 mi overlook spur); too long = a through
# trail passing by (e.g. the whole Appalachian Trail). Name matches bypass this.
PROX_MIN_MI = 0.4
PROX_MAX_MI = 14.0


def pick_trail(features, peak_name, summit, radius_mi):
    """Group by trail name; choose name match, else nearest sane-length route."""
    groups = {}
    for f in features:
        groups.setdefault(f["name"], []).append(f)

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
        length = path_len_mi(path)
        if not name_match:
            if length < PROX_MIN_MI or length > PROX_MAX_MI:
                continue  # implausible as this peak's route
        elif length > 25:
            continue  # a name-matched through-trail, not this peak's route
        # Among name matches prefer the LONGEST trail: the short ones are
        # summit spurs / final segments (Longs Peak matched a 2.7 mi piece
        # where the canonical route is ~7 mi one-way); the trail named after
        # the peak that runs longest is almost always the full route.
        scored.append((name_match, length if name_match else -near, name, path))
    if not scored:
        return None, None, False
    scored.sort(reverse=True)  # name match first; longest name match wins
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
        # Try each public-domain source in order; prefer a name match.
        name = path = None
        name_match = False
        src_attr = ""
        src_url = src_nf = src_of = None
        for label, url, nf, of, attr in SOURCES:
            feats = query_source(url, nf, of, d["lat"], d["lon"], radius_km, ctx)
            if not feats:
                continue
            n, p, nm = pick_trail(feats, d["name"], summit, radius_mi=radius_km * 0.621)
            if p and (nm or not path):   # take a name match immediately; else keep first hit
                name, path, name_match, src_attr = n, p, nm, attr
                src_url, src_nf, src_of = url, nf, of
                if nm:
                    break
        if not path:
            # Last resort: named OSM ways (state parks / local trails that
            # the federal services don't carry).
            feats = query_osm_paths(d["lat"], d["lon"], radius_km, ctx)
            if feats:
                n, p, nm = pick_trail(feats, d["name"], summit,
                                      radius_mi=radius_km * 0.621)
                if p:
                    name, path, name_match = n, p, nm
                    src_attr = "OpenStreetMap contributors (ODbL)"
                    src_url = None  # no ArcGIS name_eq expansion for OSM
        if not path:
            print(f"  · no USFS/NPS trail near {d['name']}")
            continue

        # Name-matched: refetch that trail's FULL geometry with a wide bbox —
        # the discovery bbox clips long approach routes. Use it if longer
        # (still capped by assemble()'s connectivity stitching).
        if name_match and name and name != "Unnamed" and src_url:
            full_feats = query_source(src_url, src_nf, src_of, d["lat"], d["lon"],
                                      25.0, ctx, name_eq=name)
            if full_feats:
                full_path = assemble(full_feats)
                if len(full_path) >= 2:
                    full_len = path_len_mi(full_path)
                    near = min(haversine_mi(summit, p) for p in full_path)
                    if (full_len > path_len_mi(path) and full_len <= 30
                            and near <= radius_km * 0.621):
                        path = full_path
        path = simplify(orient_to_summit(path, summit))
        eles = _ee.batch_elevations([(p[0], p[1]) for p in path], ctx)
        # batch_elevations now index-aligns its output with `path` and fills
        # None for any point whose chunk failed, rather than silently
        # dropping it (a dropped point used to misalign every point after
        # it). So the length check alone no longer proves every point has a
        # real value — a partial failure can still slip through as None.
        if len(eles) != len(path) or any(e is None for e in eles):
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
        # `dist` is one traverse of the geometry. The hiked distance — what the
        # NPS difficulty formula needs — is twice that for an out-and-back.
        # route_metrics owns this rule for every caller.
        stats["gain"] = round(max(eles) - min(eles))
        stats.pop("distance_source", None)  # freshly computed geometry
        _rm.apply_to_trail(t)
        ds = d.setdefault("data_sources", {})
        ds["gps_source"] = src_attr
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

    load_extra_sources()
    print(f"Fetching trail routes for drafts in {state} "
          f"(radius {radius_km} km, sources: {', '.join(s[0] for s in SOURCES)})…")
    ctx = ssl_context()
    n = process(state, slug, radius_km, limit, ctx)
    print(f"\nAttached routes to {n} trail(s). Now run:")
    print(f"  python3 scripts/run-pipeline.py --state {state}")
    print(f"  python3 scripts/curate-state.py {state}   # publishes the ones that pass quality")


if __name__ == "__main__":
    main()
