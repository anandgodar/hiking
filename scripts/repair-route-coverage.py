#!/usr/bin/env python3
"""
Repair trails whose stored geometry covers only a fraction of the real route.

These are curated records where the DISTANCE is correct (hand-authored from a
guidebook) but the drawn route is a fragment — Half Dome states 14.2 miles and
draws 1.7. The map contradicts the stats, and the elevation profile is built
from the fragment.

Strategy: the authored distance is the trusted value, so use it as the target.
Query every public-domain source around the summit, assemble each candidate
trail by name, and keep the candidate whose HIKED distance (via route_metrics)
best matches the authored figure. Install it only when the match is close
enough to be credible; otherwise leave the record untouched and report it, so
a human decides whether to hold it. Never synthesises geometry.

Usage:
  python3 scripts/repair-route-coverage.py --dry-run
  python3 scripts/repair-route-coverage.py --max-ratio 5      # severe only
  python3 scripts/repair-route-coverage.py --state california
"""

import glob
import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "website" / "src" / "data"
sys.path.insert(0, str(ROOT / "scripts"))
import route_metrics as rm  # noqa: E402

# A candidate must land within this fraction of the authored distance. Kept
# strict: a partial centreline that merely shares a name would otherwise
# overwrite a correct authored distance with a short one, trading a wrong map
# for wrong stats. Guidebook mileage and GIS centrelines differ a little, not
# by a quarter.
MATCH_TOLERANCE = 0.15
SEARCH_RADIUS_KM = 20.0


def load(name):
    spec = importlib.util.spec_from_file_location(
        name.replace("-", "_"), ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def affected(pattern, max_ratio, min_ratio):
    """Live trails carrying an authored distance that its geometry contradicts."""
    out = []
    for p in sorted(glob.glob(pattern)):
        try:
            d = json.loads(Path(p).read_text())
        except Exception:
            continue
        if not isinstance(d, dict) or not d.get("state_slug") or d.get("_status"):
            continue
        t = (d.get("trails") or [{}])[0]
        s = t.get("stats") or {}
        if s.get("distance_source") != "authored":
            continue
        dist = s.get("distance") or 0
        length = s.get("route_length_mi") or 0.01
        ratio = dist / max(length, 0.01)
        if min_ratio <= ratio <= max_ratio:
            out.append((ratio, Path(p), d))
    out.sort(key=lambda x: -x[0])
    return out


# Words that carry no identity — every trail is a "trail", most summits are a
# "mount". Matching on these would pair any route with any other.
STOPWORDS = {
    # structural
    "trail", "trails", "loop", "via", "to", "the", "and", "of", "route",
    "path", "spur", "road", "cutoff", "connector", "access",
    # generic summit words
    "mount", "mt", "mountain", "peak", "summit", "butte", "bald", "knob",
    # directions / qualifiers
    "north", "south", "east", "west", "upper", "lower", "old", "new",
    "big", "little", "great",
    # generic landforms — these are the false-match engine: matching on
    # "dome" paired Sentinel Dome with Half Dome, and "lake" paired Mirror
    # Lake with Elizabeth Lake.
    "dome", "lake", "lakes", "pond", "fall", "falls", "creek", "brook",
    "river", "canyon", "gorge", "ridge", "hill", "hills", "rock", "rocks",
    "point", "valley", "meadow", "meadows", "spring", "springs", "notch",
    "gap", "pass", "basin", "park", "forest", "wilderness",
}


def name_tokens(name):
    """Distinctive words identifying a specific trail."""
    cleaned = "".join(c if c.isalnum() or c.isspace() else " " for c in (name or "").lower())
    return {w for w in cleaned.split() if w not in STOPWORDS and len(w) > 2}


def best_candidate(ft, summit, target_mi, hint, ctx):
    """Assembled route that IS the named route, validated by length.

    Length agreement alone is not evidence of identity: searching purely for a
    trail of the right length paired Half Dome with the Valley Loop Trail and
    Bridalveil Fall with a hotel access path. So a candidate must first share a
    distinctive name token with the route the record names, and only then is
    its length used to choose among the survivors.
    """
    wanted = name_tokens(hint)
    if not wanted:
        return None
    best = None
    for label, url, name_field, order_field, attr in ft.SOURCES + (ft.load_extra_sources() or []):
        try:
            feats = ft.query_source(url, name_field, order_field,
                                    summit[0], summit[1], SEARCH_RADIUS_KM, ctx)
        except Exception:
            continue
        if not feats:
            continue
        # Group segments by trail name and assemble each separately.
        by_name = {}
        for f in feats:
            if f.get("name"):
                by_name.setdefault(f["name"], []).append(f)
        for name, group in by_name.items():
            # Identity first: this must be the route the record names.
            if not (name_tokens(name) & wanted):
                continue
            path = ft.assemble(group)
            if not path or len(path) < 2:
                continue
            near = min(ft.haversine_mi(summit, p) for p in path)
            if near > SEARCH_RADIUS_KM * 0.62:
                continue  # doesn't reach this peak
            hiked, _, _ = rm.hiked_distance_mi(path)
            error = abs(hiked - target_mi) / target_mi
            score = (error,)
            if best is None or score < best[0]:
                best = (score, path, attr, name, hiked)
    return best


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    max_ratio = float(args[args.index("--max-ratio") + 1]) if "--max-ratio" in args else 1e9
    min_ratio = float(args[args.index("--min-ratio") + 1]) if "--min-ratio" in args else 2.0
    state = args[args.index("--state") + 1] if "--state" in args else None
    pattern = str(DATA / (state or "*") / "*.json")

    ft = load("fetch-trails")
    ee = load("enrich-elevation")
    ctx = ft.ssl_context()

    targets = affected(pattern, max_ratio, min_ratio)
    print(f"{len(targets)} trail(s) with contradicted geometry "
          f"(ratio {min_ratio}–{max_ratio})\n")

    repaired = unmatched = 0
    for ratio, path_file, d in targets:
        t = d["trails"][0]
        stats = t["stats"]
        target = stats["distance"]
        summit = [d["lat"], d["lon"]]
        print(f"· {d['name'][:30]:32} authored {target} mi, geometry "
              f"{stats.get('route_length_mi')} mi ({ratio:.0f}x)")
        best = best_candidate(ft, summit, target, t.get("name"), ctx)
        if not best:
            print("    no candidate route found in public sources")
            unmatched += 1
            continue
        (error,), cand_path, attr, name, hiked = best
        if error > MATCH_TOLERANCE:
            print(f"    best candidate \"{name[:34]}\" = {hiked} mi "
                  f"({error*100:.0f}% off) — rejected, leaving record untouched")
            unmatched += 1
            continue
        if dry:
            print(f"    would install \"{name[:34]}\" = {hiked} mi "
                  f"({error*100:.0f}% off target)")
            repaired += 1
            continue

        raw_len = ft.path_len_mi(cand_path)
        maxn = max(120, min(900, int(raw_len * 60)))
        cand_path = ft.simplify(ft.orient_to_summit(cand_path, summit), maxn=maxn)
        eles = ee.batch_elevations([(p[0], p[1]) for p in cand_path], ctx)
        if len(eles) != len(cand_path) or any(e is None for e in eles):
            print("    elevation fetch failed — skipped")
            unmatched += 1
            continue
        path3 = [[p[0], p[1], round(e)] for p, e in zip(cand_path, eles)]
        geo = t.setdefault("geo", {})
        geo["path"] = path3
        geo["chart"] = ee.build_chart(path3)
        geo.setdefault("markers", {})["summit"] = summit
        geo["markers"]["start"] = [path3[0][0], path3[0][1]]
        stats["gain"] = round(max(eles) - min(eles))
        # Geometry now covers the route, so the distance is computed again.
        stats.pop("distance_source", None)
        rm.apply_to_trail(t)
        ds = d.setdefault("data_sources", {})
        ds["gps_source"] = attr
        ds["route_verified"] = str(date.today())
        path_file.write_text(json.dumps(d, indent=2) + "\n")
        print(f"    ✅ installed \"{name[:34]}\" — {stats['distance']} mi "
              f"{stats['distance_type']} ({error*100:.0f}% off authored)")
        repaired += 1

    print(f"\n{'[dry-run] ' if dry else ''}repaired: {repaired} | "
          f"left for review: {unmatched}")
    if unmatched:
        print("Records left untouched keep their authored distance and short "
              "geometry; hold them if the map would mislead.")


if __name__ == "__main__":
    main()
