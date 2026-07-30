#!/usr/bin/env python3
"""
Install a specific, named official trail as a peak's route.

For marquee peaks the automatic name-matcher can pick a summit fragment
("Pikes Peak" segment, 0.9 mi) instead of the real standard route ("Barr
Trail", ~12.6 mi) because the route's name doesn't contain the peak's name.
This tool fetches ONE explicitly named trail from the public-domain sources
(USFS/NPS/USGS + trail-sources.json extras), stitches its segments, and
REPLACES the peak's existing route. Same data standards as fetch-trails:
real geometry only, DEM elevations, source attribution recorded.

Usage:
  python3 scripts/fetch-named-route.py <state> <slug> "<official trail name>" [--radius-km 25]
  python3 scripts/fetch-named-route.py colorado pikes-peak-co "Barr" --radius-km 25
"""

import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "website" / "src" / "data"


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"),
                                                  ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    args = [a for a in sys.argv[1:]]
    radius_km = 25.0
    if "--radius-km" in args:
        i = args.index("--radius-km")
        radius_km = float(args[i + 1])
        args = args[:i] + args[i + 2:]
    if len(args) != 3:
        sys.exit(__doc__)
    state, slug, trail_name = args

    ft = load("fetch-trails")
    ee = load("enrich-elevation")
    ctx = ft.ssl_context()

    path_file = None
    for f in sorted((DATA / state).glob("*.json")):
        d = json.loads(f.read_text())
        if d.get("slug") == slug:
            path_file = f
            break
    if not path_file:
        sys.exit(f"no trail file with slug {slug} in {state}")
    summit = [d["lat"], d["lon"]]

    best = None  # (path, src_attr, matched_name)
    for label, url, name_field, order_field, attr in ft.SOURCES + (ft.load_extra_sources() or []):
        feats = ft.query_source(url, name_field, order_field, summit[0], summit[1],
                                radius_km, ctx, name_eq=trail_name)
        if not feats:
            continue
        path = ft.assemble(feats)
        if not path or len(path) < 2:
            continue
        length = ft.path_len_mi(path)
        near = min(ft.haversine_mi(summit, p) for p in path)
        print(f"  {label}: \"{feats[0]['name']}\" {round(length,1)} mi, "
              f"nearest point {round(near,1)} mi from summit")
        if length < 0.5 or length > 30 or near > radius_km * 0.7:
            continue
        if not best or length > ft.path_len_mi(best[0]):
            best = (path, attr, feats[0]["name"])
    if not best:
        sys.exit("❌ no usable geometry found — try another name or radius")

    path, attr, matched = best
    # Long switchbacked routes (Barr's "Ws") lose real distance if crushed to
    # 120 points — budget ~25 points/mile instead.
    raw_len = ft.path_len_mi(path)
    maxn = max(120, min(900, int(raw_len * 60)))
    path = ft.simplify(ft.orient_to_summit(path, summit), maxn=maxn)
    eles = ee.batch_elevations([(p[0], p[1]) for p in path], ctx)
    if len(eles) != len(path):
        sys.exit("❌ elevation fetch failed")
    path3 = [[p[0], p[1], round(e)] for p, e in zip(path, eles)]
    dist = sum(ft.haversine_mi(path3[i - 1], path3[i]) for i in range(1, len(path3)))

    t = d["trails"][0]
    geo = t.setdefault("geo", {})
    geo["path"] = path3
    geo["chart"] = ee.build_chart(path3)
    geo.setdefault("markers", {})["summit"] = summit
    geo["markers"]["start"] = [path3[0][0], path3[0][1]]
    stats = t.setdefault("stats", {})
    stats["gain"] = round(max(eles) - min(eles))
    sys.path.insert(0, str(ROOT / "scripts"))
    import route_metrics as rm
    stats.pop("distance_source", None)  # freshly computed geometry
    rm.apply_to_trail(t)
    dist = stats["distance"]
    pretty = matched.title() if matched.isupper() else matched
    t["name"] = pretty if pretty.lower().endswith("trail") else f"{pretty} Trail"
    ds = d.setdefault("data_sources", {})
    ds["gps_source"] = attr
    ds["elevation_source"] = "Open-Meteo (Copernicus 30 m DEM)"
    ds["route_verified"] = str(date.today())
    path_file.write_text(json.dumps(d, indent=2) + "\n")
    print(f"✅ {d['name']}: installed \"{matched}\" — {round(dist,1)} mi, "
          f"{stats['gain']} ft gain ({attr})")
    print(f"   now run: python3 scripts/run-pipeline.py --state {state}")


if __name__ == "__main__":
    main()
