#!/usr/bin/env python3
"""
Curate & publish a state's trails. The quality gate decides publish vs draft.

Actions:
  curate-state.py <state>              # PUBLISH pass: auto-publish every trail
                                       #   that meets the quality bar; keep the
                                       #   rest as drafts for review.
  curate-state.py <state> published    # list trails currently live on the site
  curate-state.py <state> draft        # list drafts + why each is held back
  curate-state.py <state> prune [...]  # rank imported peaks by notability and
                                       #   move the noise to _rejected/ (see below)

Auto-publish quality bar (all must pass):
  * real GPS route (geo.path non-empty)        — a trail guide needs a route
  * distance > 0 and elevation gain present     — usually auto-filled from GPX
  * valid summit coordinate + elevation
  * GPS-audit score >= quality.min_score (pipeline.config.json)
Difficulty, if missing, is COMPUTED from distance+gain via the standard NPS
numerical rating — not invented. Publishing removes the `_status` flag; the
frontend then shows the trail. Trails that fail the bar keep `_status` and stay
hidden until enriched (drop a real GPX → run-pipeline → re-run this).

prune options:  --keep-top N | --min-prominence M | --apply
"""

import importlib.util
import json
import math
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "website" / "src" / "data"
GENERIC_NAME = re.compile(r"\b(hill|knob|rise|ridge|mound)\b", re.I)

# Real, publicly documented coordinates of population centers, used ONLY as a
# prune-ranking signal (never written into a trail record). For states where
# OSM peak metadata alone can't distinguish a well-known local trailhead peak
# from a remote unranked summit — Wolverine Peak and Flattop Mountain near
# Anchorage carry no prominence or wikidata tag at all, so a metadata-only
# ranking puts them near the BOTTOM of 1,200+ Alaska candidates — proximity
# to where people actually live is a legitimate, unfabricated proxy for
# "likely to have a maintained trail."
POPULATION_CENTERS = {
    "alaska": [
        ("Anchorage", 61.2181, -149.9003), ("Fairbanks", 64.8378, -147.7164),
        ("Juneau", 58.3019, -134.4197), ("Sitka", 57.0531, -135.3300),
        ("Ketchikan", 55.3422, -131.6461), ("Wasilla", 61.5814, -149.4394),
        ("Kenai", 60.5544, -151.2583), ("Palmer", 61.5997, -149.1123),
        ("Homer", 59.6425, -151.5483), ("Seward", 60.1042, -149.4422),
    ],
}


def _hav_mi(a_lat, a_lon, b_lat, b_lon):
    r = 3959
    dlat = math.radians(b_lat - a_lat)
    dlon = math.radians(b_lon - a_lon)
    h = (math.sin(dlat / 2) ** 2 + math.cos(math.radians(a_lat))
         * math.cos(math.radians(b_lat)) * math.sin(dlon / 2) ** 2)
    return r * 2 * math.asin(math.sqrt(h))


def nearest_population_center_mi(state, rec):
    centers = POPULATION_CENTERS.get(state)
    if not centers or rec.get("lat") is None or rec.get("lon") is None:
        return None
    return min(_hav_mi(c[1], c[2], rec["lat"], rec["lon"]) for c in centers)


def load_audit():
    spec = importlib.util.spec_from_file_location(
        "audit", ROOT / "scripts" / "audit-gps-quality.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def min_score():
    cfg = ROOT / "pipeline.config.json"
    if cfg.exists():
        return json.loads(cfg.read_text()).get("quality", {}).get("min_score", 80)
    return 80


def load(state):
    items = []
    for f in sorted((DATA / state).glob("*.json")):
        try:
            items.append((f, json.loads(f.read_text())))
        except json.JSONDecodeError:
            continue
    return items


# ---- difficulty (computed, not invented) --------------------------------
def compute_difficulty(distance, gain):
    """NPS/Shenandoah numerical rating: sqrt(2 * gain_ft * distance_mi)."""
    if not distance or not gain:
        return None
    r = math.sqrt(2 * gain * distance)
    if r < 50:
        return "Easy"
    if r < 100:
        return "Moderate"
    if r < 150:
        return "Hard"
    return "Strenuous"


# ---- publish quality assessment -----------------------------------------
def assess(rec, audit_mod, threshold):
    """Return [] if publishable, else a list of blocking reasons."""
    reasons = []
    t = (rec.get("trails") or [{}])[0]
    geo = t.get("geo") or {}
    stats = t.get("stats") or {}
    if not (isinstance(geo.get("path"), list) and geo.get("path")):
        reasons.append("no GPS route (drop gpx-downloads/<slug>.gpx, run pipeline)")
    dist = stats.get("distance")
    if not dist:
        reasons.append("no distance")
    elif dist < 0.3:
        # A sub-0.3 mi "route" is almost always a data fragment (a trail
        # segment endpoint), not a hike worth a page — thin content.
        reasons.append(f"route too short ({dist} mi) — likely a fragment")
    if not stats.get("gain"):
        reasons.append("no elevation gain")
    elif dist and stats["gain"] / dist > 1300:
        # Sustained hiking trails top out around 1,000–1,200 ft/mi (Huntington
        # Ravine class). Steeper means a climbing/mountaineering line got
        # matched (e.g. a route up Denali's flank) — not publishable as a hike.
        reasons.append(f"implausibly steep ({round(stats['gain']/dist)} ft/mi) "
                       "— likely a climbing route, not a hiking trail")
    if rec.get("lat") is None or rec.get("lon") is None:
        reasons.append("no coordinates")
    elev = rec.get("elevation")
    if elev is None or elev <= 0:
        # 0/None isn't a credible summit elevation (lowest US point is -282 ft
        # in Death Valley, but a 0 here means missing data, not a real basin).
        reasons.append("no credible elevation (run enrich-elevation to backfill)")
    # Only run the GPS audit if a route exists (otherwise it's trivially 0).
    if isinstance(geo.get("path"), list) and geo.get("path"):
        r = audit_mod.audit_route(t)
        if r["score"] < threshold:
            reasons.append(f"GPS quality {r['score']} < {threshold}")
    return reasons


def do_publish(state):
    audit_mod = load_audit()
    threshold = min_score()
    items = load(state)
    published_now, already, drafts = [], [], []

    demoted = []
    for f, rec in items:
        if not rec.get("name"):
            continue
        if not rec.get("_status"):
            # Re-check IMPORTED live trails against the (possibly tightened)
            # gate and demote failures back to draft. Hand-curated trails
            # (no `osm` block) are never demoted automatically.
            if rec.get("osm"):
                reasons = assess(rec, audit_mod, threshold)
                if reasons:
                    rec["_status"] = f"demoted — {reasons[0]}"
                    f.write_text(json.dumps(rec, indent=2) + "\n")
                    demoted.append((rec["name"], reasons))
                    continue
            already.append(rec["name"])
            continue
        reasons = assess(rec, audit_mod, threshold)
        if reasons:
            drafts.append((rec["name"], reasons))
            continue
        # Passes the bar → finalize and publish.
        t = rec["trails"][0]
        stats = t.setdefault("stats", {})
        if not (t.get("difficulty") or stats.get("difficulty")):
            diff = compute_difficulty(stats.get("distance"), stats.get("gain"))
            if diff:
                t["difficulty"] = diff
                stats["difficulty"] = diff
        if not stats.get("time") and stats.get("distance"):
            # Naismith's rule: 3 mph + 1 hr per 2,000 ft of ascent.
            hours = stats["distance"] / 3.0 + (stats.get("gain") or 0) / 2000.0
            stats["time"] = round(max(0.5, hours) * 2) / 2
        rec.pop("_status", None)
        f.write_text(json.dumps(rec, indent=2) + "\n")
        published_now.append(rec["name"])

    print(f"State: {state}")
    print(f"  ✅ published now: {len(published_now)}")
    for n in published_now[:40]:
        print(f"       + {n}")
    print(f"  • already live:  {len(already)}")
    if demoted:
        print(f"  ⬇️  demoted to draft: {len(demoted)}")
        for n, reasons in demoted[:20]:
            print(f"       - {n}: {reasons[0]}")
    print(f"  ⏳ held as draft: {len(drafts)}")
    for n, reasons in drafts[:40]:
        print(f"       - {n}: {reasons[0]}")
    print(f"\n  Live now: {len(published_now) + len(already)}  ·  "
          f"Draft: {len(drafts)}")
    print(f"  Rebuild to see changes:  cd website && npm run build")
    if drafts:
        print(f"  Enrich drafts: add a real GPX per trail, run "
              f"`python3 scripts/run-pipeline.py --state {state}`, then re-run this.")


def is_live(rec):
    t = (rec.get("trails") or [{}])[0]
    geo = t.get("geo") or {}
    stats = t.get("stats") or {}
    return (not rec.get("_status")
            and isinstance(geo.get("path"), list) and geo.get("path")
            and isinstance(stats.get("distance"), (int, float)) and stats.get("distance") > 0)


def do_list(state, want_live):
    audit_mod = load_audit()
    threshold = min_score()
    rows = []
    for f, rec in load(state):
        if not rec.get("name"):
            continue
        live = is_live(rec)
        if live != want_live:
            continue
        if want_live:
            rows.append(f"  ✓ {rec['name']}")
        else:
            reasons = assess(rec, audit_mod, threshold) or ["needs review"]
            rows.append(f"  - {rec['name']}: {', '.join(reasons)}")
    label = "PUBLISHED" if want_live else "DRAFT"
    print(f"{label} trails in {state}: {len(rows)}")
    print("\n".join(rows))


# ---- notability pruning (moved under the `prune` action) -----------------
def prominence_m(rec):
    raw = (rec.get("osm") or {}).get("prominence_m")
    if not raw:
        return None
    m = re.match(r"[-+]?[0-9]*\.?[0-9]+", str(raw))
    return float(m.group()) if m else None


def notability(rec, weight_elevation=True):
    """Rank peaks by how notable/hikeable they are, not just how tall.

    weight_elevation=True (default) is right for most states: within a
    region of comparable peaks, taller usually means better-known. It is
    wrong for a state whose import band already spans "hikeable" to
    "mountaineering objective" (Alaska with max_ele=8000 still includes
    7,000+ ft technical peaks) — there, the elevation term drowns out
    prominence and silently re-imposes a tallest-first ranking, cutting
    real hiking destinations like Flattop Mountain (3,510 ft) in favor of
    remote unranked 7,000+ ft summits with no trail. Pass False to rank
    on prominence/wikidata notability alone within the elevation band the
    import step already applied.
    """
    score = 0.0
    prom = prominence_m(rec)
    if prom is not None:
        score += prom
    if (rec.get("osm") or {}).get("wikidata"):
        score += 300
    if weight_elevation:
        score += (rec.get("elevation") or 0) / 100.0
    if GENERIC_NAME.search(rec.get("name", "")):
        score -= 100
    return score


def do_prune(state, opts):
    items = load(state)
    imported = [(f, r) for f, r in items if r.get("osm")]
    handmade = [(f, r) for f, r in items if not r.get("osm")]
    weight_elev = not opts.get("ignore_elevation")
    near_pop = opts.get("near_population_mi")
    far_cut = []
    if near_pop is not None:
        before = len(imported)
        near, far = [], []
        for f, r in imported:
            (near if (nearest_population_center_mi(state, r) or 1e9) <= near_pop
             else far).append((f, r))
        # Excluded-by-distance candidates are CUT, not silently left in
        # place — leaving them untouched here previously meant a directory
        # of 1,223 files reported "keep 60" and still had 1,021 on disk.
        far_cut = [(f, r, prominence_m(r)) for f, r in far]
        imported = near
        print(f"  proximity filter: {before} -> {len(imported)} within "
              f"{near_pop} mi of a population center ({len(far)} cut)")
    ranked = sorted(imported, key=lambda fr: notability(fr[1], weight_elev), reverse=True)

    keep, cut = [], list(far_cut)
    for rank, (f, r) in enumerate(ranked):
        prom = prominence_m(r)
        if opts["min_prominence"] is not None:
            is_keep = prom is not None and prom >= opts["min_prominence"]
        elif opts["keep_top"] is not None:
            is_keep = rank < opts["keep_top"]
        else:
            is_keep = (prom is not None and prom >= 100) or bool((r.get("osm") or {}).get("wikidata"))
        (keep if is_keep else cut).append((f, r, prom))

    print(f"State: {state}  |  imported {len(imported)} → keep {len(keep)}, "
          f"cut {len(cut)}  (hand-curated kept: {len(handmade)})")
    for f, r, prom in cut[:15]:
        print(f"    ✗ {r['name']:<30} prom={prom if prom is not None else '-'}m")
    if not opts["apply"]:
        print("  (report only — add --apply to move CUT files to _rejected/)")
        return
    rej = DATA / "_rejected" / state
    rej.mkdir(parents=True, exist_ok=True)
    for f, r, prom in cut:
        shutil.move(str(f), str(rej / f.name))
    print(f"✅ Moved {len(cut)} to _rejected/{state}/ (reversible).")


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit("Usage: curate-state.py <state> [published|draft|prune] [options]")
    state = args[0]
    rest = args[1:]
    if not (DATA / state).is_dir():
        sys.exit(f"❌ No data folder for '{state}'")

    action = rest[0] if rest and not rest[0].startswith("-") else "publish"

    if action == "published":
        do_list(state, want_live=True)
    elif action == "draft":
        do_list(state, want_live=False)
    elif action == "prune":
        opts = {"keep_top": None, "min_prominence": None, "apply": False,
                "ignore_elevation": False, "near_population_mi": None}
        i = 0
        while i < len(rest):
            a = rest[i]
            if a == "--keep-top":
                opts["keep_top"] = int(rest[i + 1]); i += 2
            elif a == "--min-prominence":
                opts["min_prominence"] = float(rest[i + 1]); i += 2
            elif a == "--apply":
                opts["apply"] = True; i += 1
            elif a == "--ignore-elevation":
                # Rank by prominence/wikidata only — for states whose import
                # elevation band already spans hikeable-to-technical, where
                # raw elevation would just re-impose tallest-first ranking.
                opts["ignore_elevation"] = True; i += 1
            elif a == "--near-population":
                # Restrict candidates to within N miles of a population
                # center (see POPULATION_CENTERS) before ranking. Real,
                # documented city coordinates — not a fabricated signal.
                opts["near_population_mi"] = float(rest[i + 1]); i += 2
            else:
                i += 1
        do_prune(state, opts)
    else:
        do_publish(state)


if __name__ == "__main__":
    main()
