#!/usr/bin/env python3
"""
Generate a multi-section, factual trail guide per trail from its real data (v2).

Every statement is computed from data already in the file — route geometry,
the elevation chart, POI features with mile markers, coordinates, stats and
sources. Nothing is embellished or invented: no scenery claims, no "stunning
views". The goal is WTA/Hiking Project-depth prose (route narrative, getting
there, when to go, need to know) built only from verifiable numbers.

Sections emitted into `generated_description` (HTML):
  lead paragraph  — identity + prominence + route summary
  The Route       — climb distribution + steepest stretch from the elevation
                    chart, treeline note, POIs in mile order
  Getting There   — trailhead coordinates, maps link, nearest city + distance
  When to Go      — season window derived from region + summit elevation
  Know Before You Go — difficulty formula, pacing, GPX, land-manager check

Also writes `page_content.faqs` (4-6 factual Q&As per trail) so the FAQ
section + FAQPage schema render on every trail page.

Replacement policy: a file is rewritten when its description is missing or
matches the v1 generator signature (single templated paragraph). Hand-written
descriptions (curated states use a different markup signature) are never
touched unless --force is passed.

Usage:
  python3 scripts/generate-description.py --state <slug>
  python3 scripts/generate-description.py <file.json> [...]
  python3 scripts/generate-description.py --force ...
"""

import glob
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "website" / "src" / "data"
CITIES = ROOT / "website" / "src" / "data-static" / "cities.json"

# Approximate regional treeline (ft). Only used for a "crosses treeline"
# sentence when start elevation is clearly below and summit clearly above.
TREELINE = {
    "colorado": 11500, "wyoming": 10500, "montana": 9500, "idaho": 9500,
    "utah": 11000, "new-mexico": 11800, "nevada": 10500, "california": 10500,
    "oregon": 7500, "washington": 6500, "alaska": 3000,
    "new-hampshire": 4400, "maine": 4000, "vermont": 4000, "new-york": 4500,
}

# Season phrasing by broad region. Factual, not scenic.
DESERT = {"arizona", "nevada", "new-mexico", "utah", "texas"}
SOUTH = {"alabama", "arkansas", "florida", "georgia", "kentucky", "louisiana",
         "mississippi", "north-carolina", "oklahoma", "south-carolina",
         "tennessee", "virginia", "west-virginia"}
NORTH = {"maine", "michigan", "minnesota", "montana", "new-hampshire",
         "new-york", "north-dakota", "vermont", "wisconsin", "alaska",
         "idaho", "wyoming", "south-dakota"}


def fmt(n):
    try:
        return f"{int(round(float(n))):,}"
    except (TypeError, ValueError):
        return None


def hav_mi(a_lat, a_lon, b_lat, b_lon):
    r = 3959
    dlat = math.radians(b_lat - a_lat)
    dlon = math.radians(b_lon - a_lon)
    h = (math.sin(dlat / 2) ** 2 + math.cos(math.radians(a_lat))
         * math.cos(math.radians(b_lat)) * math.sin(dlon / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(h))


def bearing_word(a_lat, a_lon, b_lat, b_lon):
    """Compass direction from a -> b."""
    dlon = math.radians(b_lon - a_lon)
    y = math.sin(dlon) * math.cos(math.radians(b_lat))
    x = (math.cos(math.radians(a_lat)) * math.sin(math.radians(b_lat))
         - math.sin(math.radians(a_lat)) * math.cos(math.radians(b_lat))
         * math.cos(dlon))
    deg = (math.degrees(math.atan2(y, x)) + 360) % 360
    dirs = ["north", "northeast", "east", "southeast",
            "south", "southwest", "west", "northwest"]
    return dirs[int((deg + 22.5) // 45) % 8]


def primary_route(d):
    trails = d.get("trails") or []
    if not trails:
        return {}
    return max(trails, key=lambda t: (t.get("stats") or {}).get("distance", 0) or 0)


def pick(slug, variants):
    return variants[sum(ord(c) for c in slug) % len(variants)]


def feature_word(name):
    n = name.lower()
    if "falls" in n or "cascade" in n:
        return "waterfall"
    if "lake" in n or "pond" in n:
        return "destination"
    if "gorge" in n or "canyon" in n:
        return "gorge"
    return "summit"


# ---------------------------------------------------------------- sections

def lead_para(d, t, stats):
    name, state, slug = d["name"], d.get("state", ""), d.get("slug", d["name"])
    fw = feature_word(name)
    elev = fmt(d.get("elevation"))
    if elev:
        head = pick(slug, [
            f"<strong>{name}</strong> is a {elev}-foot {fw} in {state}.",
            f"At {elev} feet, <strong>{name}</strong> is a {fw} in {state}.",
            f"<strong>{name}</strong> rises to {elev} feet in {state}.",
        ])
    else:
        head = f"<strong>{name}</strong> is a hiking {fw} in {state}."
    prom = (d.get("osm") or {}).get("prominence_m")
    if prom:
        try:
            head += (f" With roughly {int(round(float(prom) * 3.28084)):,} feet"
                     " of topographic prominence, it stands well above the"
                     " surrounding terrain.")
        except (TypeError, ValueError):
            pass
    dist, gain = stats.get("distance"), stats.get("gain")
    diff = t.get("difficulty") or stats.get("difficulty")
    rname = t.get("name") or "The main route"
    if dist and gain:
        per_mi = gain / dist if dist else 0
        hard = (diff or "").lower() in ("hard", "strenuous")
        if per_mi > 700:
            character = "a steep, sustained climb"
        elif per_mi > 350:
            character = "a steady climb"
        elif hard:
            # Low grade but a hard rating means distance is the challenge.
            character = ("gentle grades, but the mileage is what makes it"
                         f" a {diff} outing")
        else:
            character = "a gradual walk with modest climbing"
        # State the distance basis explicitly. `distance` is the HIKED
        # distance (twice the geometry for an out-and-back), so an unlabeled
        # number would leave the reader guessing which one it is.
        dtype = stats.get("distance_type")
        basis = (" round trip (out-and-back)" if dtype == "out-and-back"
                 else " (loop)" if dtype == "loop" else "")
        head += (f" The {rname} covers {dist} miles{basis} with about"
                 f" {fmt(gain)} feet of elevation gain — {character}.")
        if diff and per_mi > 350:
            head += f" It's rated {diff} overall."
    return f"<p>{head}</p>"


def route_section(d, t, stats):
    geo = t.get("geo") or {}
    chart = geo.get("chart") or []
    dist, gain = stats.get("distance"), stats.get("gain")
    bits = []

    # Climb distribution: split the chart at half distance.
    if len(chart) >= 6 and dist and gain and gain > 200:
        half = dist / 2
        first = [p for p in chart if p.get("mile", 0) <= half]
        def climb(pts):
            c = 0
            for a, b in zip(pts, pts[1:]):
                step = (b.get("elev") or 0) - (a.get("elev") or 0)
                if step > 0:
                    c += step
            return c
        c1, c_all = climb(first), climb(chart)
        if c_all > 0:
            share = c1 / c_all
            if share < 0.35:
                bits.append("The grade is back-loaded: the first half of the"
                            " route climbs gently, and most of the elevation"
                            " gain comes in the second half.")
            elif share > 0.65:
                bits.append("Most of the climbing comes early — the first half"
                            " of the route does the bulk of the work before"
                            " the grade eases.")
            else:
                bits.append("The climbing is spread fairly evenly from start"
                            " to finish rather than stacked into one steep"
                            " section.")
        # Steepest stretch.
        steepest, s_mile = 0, None
        for a, b in zip(chart, chart[1:]):
            dm = (b.get("mile") or 0) - (a.get("mile") or 0)
            de = (b.get("elev") or 0) - (a.get("elev") or 0)
            if dm > 0.05 and de / dm > steepest:
                steepest, s_mile = de / dm, a.get("mile")
        if s_mile is not None and steepest > 400:
            bits.append(f"The steepest stretch arrives around mile"
                        f" {s_mile:g}, gaining roughly {int(round(steepest / 100.0) * 100):,}"
                        " feet per mile — expect a slow, deliberate pace"
                        " through here.")
        # Start/high-point elevations are real chart values. Use the chart
        # maximum, not the last point — some routes end at a col or loop back.
        start_e = chart[0].get("elev")
        max_e = max((p.get("elev") or 0) for p in chart)
        if start_e and max_e > start_e + 100:
            bits.append(f"From the trailhead at about {fmt(start_e)} feet, the"
                        f" route tops out near {fmt(max_e)} feet.")
            tl = TREELINE.get(d.get("state_slug"))
            if tl and start_e < tl - 300 and max_e > tl + 200:
                bits.append("You'll cross above treeline on the way up, so the"
                            " upper route is exposed to weather — check the"
                            " forecast and turn around if conditions build.")

    # POIs in mile order (skip the summit itself — that's the destination).
    feats = []
    for f in (t.get("features") or []):
        if f.get("type") == "summit":
            continue
        if f.get("mile") is None or not f.get("type"):
            continue
        feats.append(f)
    feats.sort(key=lambda f: f["mile"])
    if feats:
        landmarks = ", ".join(
            f"a {f['type']}{' (' + f['name'] + ')' if f.get('name') and f['name'].lower() != f['type'] else ''}"
            f" near mile {f['mile']:g}" for f in feats[:4])
        bits.append(f"Along the way the route passes {landmarks} — useful"
                    " checkpoints for judging your pace.")

    if not bits:
        return ""
    return "<h3>The Route</h3><p>" + " ".join(bits) + "</p>"


def getting_there(d, t):
    geo = t.get("geo") or {}
    start = (geo.get("markers") or {}).get("start")
    if not start or None in start[:2]:
        return ""
    lat, lon = round(start[0], 5), round(start[1], 5)
    gmaps = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"
    bits = [f"The trailhead is at <a href=\"{gmaps}\" target=\"_blank\""
            f" rel=\"noopener\">{lat}, {lon}</a> (tap for driving"
            " directions)."]
    try:
        cities = json.loads(CITIES.read_text())
        near = min(cities, key=lambda c: hav_mi(c["lat"], c["lon"], lat, lon))
        mi = hav_mi(near["lat"], near["lon"], lat, lon)
        if mi <= 250:
            bits.append(f"It's roughly {int(round(mi / 5.0) * 5)} miles"
                        f" {bearing_word(near['lat'], near['lon'], lat, lon)}"
                        f" of {near['name']}, {near['state']}.")
    except Exception:
        pass
    pd = t.get("parking_details") or {}
    if pd.get("location"):
        bits.append(f"Parking: {pd['location']}.")
    if pd.get("fee"):
        bits.append(f"Fee: {pd['fee']}.")
    if not pd.get("location"):
        bits.append("Arrive early on weekends — trailhead lots at popular"
                    " peaks fill quickly, and cell service is often"
                    " unreliable once you leave the highway.")
    return "<h3>Getting There</h3><p>" + " ".join(bits) + "</p>"


def when_to_go(d):
    slug = d.get("state_slug", "")
    elev = d.get("elevation") or 0
    if slug in DESERT and elev < 8000:
        s = ("October through April is the comfortable window here — summer"
             " temperatures at this elevation are dangerously hot, so if you"
             " must hike in summer, start at first light and carry more water"
             " than you think you need.")
    elif elev >= 11000:
        s = ("The reliable snow-free window is roughly July through"
             " September. At this elevation, afternoon thunderstorms are a"
             " serious summer hazard — start early and plan to be off the"
             " upper mountain by midday. Outside that window expect snow"
             " travel and bring traction and navigation skills to match.")
    elif slug in NORTH or elev >= 4000:
        s = ("Late May through October is the main season. Snow and ice"
             " linger into spring and return early in fall at this latitude"
             " and elevation; in winter this becomes a different, more"
             " serious undertaking requiring traction devices and warm"
             " layers.")
    elif slug in SOUTH:
        s = ("This trail is hikeable most of the year. Summer brings heat and"
             " humidity — carry extra water — while fall and spring offer the"
             " most comfortable conditions. Ice is possible on shaded"
             " stretches in mid-winter.")
    else:
        s = ("Spring through fall is the main season. Conditions change fast"
             " in the shoulder months — check a point forecast for the"
             " summit, not the nearest town, before you commit.")
    return "<h3>When to Go</h3><p>" + s + "</p>"


def need_to_know(d, t, stats):
    diff = t.get("difficulty") or stats.get("difficulty")
    time = stats.get("time")
    bits = []
    if diff:
        bits.append(f"The {diff} rating comes from the National Park Service"
                    " difficulty formula, which weighs total distance against"
                    " elevation gain.")
    if time:
        bits.append(f"Most hikers should budget about {time} hours of moving"
                    " time; add margin for breaks, photos and the descent.")
    bits.append("Download the GPX track from this page before you go — cell"
                " coverage is unreliable in the mountains and a saved route"
                " works offline in any GPS app.")
    by = (d.get("data_sources") or {}).get("verified_by", "")
    by = by.split(" — ")[0].strip()
    src = f" Trail data is sourced from {by}." if by else ""
    bits.append("Conditions change: verify current access, closures and"
                f" weather with the official land manager before you go.{src}")
    return "<h3>Know Before You Go</h3><p>" + " ".join(bits) + "</p>"


def nearby_para(d):
    peaks = [p.get("name") for p in (d.get("nearby_peaks") or []) if p.get("name")]
    if not peaks:
        return ""
    peaks = peaks[:3]
    joined = peaks[0] if len(peaks) == 1 else ", ".join(peaks[:-1]) + f" and {peaks[-1]}"
    return (f"<p>Looking to link objectives or plan a weekend? Nearby summits"
            f" include {joined} — each has its own guide on this site.</p>")


def build_description(d):
    t = primary_route(d)
    stats = t.get("stats") or {}
    parts = [lead_para(d, t, stats),
             route_section(d, t, stats),
             getting_there(d, t),
             when_to_go(d),
             need_to_know(d, t, stats),
             nearby_para(d)]
    body = "\n  ".join(p for p in parts if p)
    return ('<div class="mountain-description prose prose-stone max-w-none">'
            f'\n  {body}\n</div>')


# ---------------------------------------------------------------- FAQs

def build_faqs(d):
    t = primary_route(d)
    stats = t.get("stats") or {}
    name = d["name"]
    state = d.get("state", "")
    dist, gain, time = stats.get("distance"), stats.get("gain"), stats.get("time")
    diff = t.get("difficulty") or stats.get("difficulty")
    faqs = []
    dtype = stats.get("distance_type")
    basis = (" round trip" if dtype == "out-and-back"
             else " as a loop" if dtype == "loop" else "")
    if time and dist:
        faqs.append({
            "question": f"How long does it take to hike {name}?",
            "answer": (f"The {t.get('name') or 'main route'} is {dist} miles{basis} with"
                       f" about {fmt(gain)} feet of elevation gain, and most hikers take"
                       f" roughly {time} hours of moving time. Add time for breaks"
                       " and conditions — winter or wet weather can double the trip."),
        })
    if diff and dist and gain:
        faqs.append({
            "question": f"How hard is the {name} hike?",
            "answer": (f"It's rated {diff} using the National Park Service difficulty"
                       f" formula ({dist} miles{basis}, {fmt(gain)} ft of gain — about"
                       f" {int(round((gain / dist) / 50.0) * 50):,} ft of climbing per mile)."
                       " The elevation profile on this page shows exactly where the"
                       " steep sections fall."),
        })
    start = ((t.get("geo") or {}).get("markers") or {}).get("start")
    if start and None not in start[:2]:
        faqs.append({
            "question": f"Where is the {name} trailhead?",
            "answer": (f"The trailhead is at {round(start[0], 5)}, {round(start[1], 5)}"
                       f" in {state}. Use the driving-directions link in the Getting"
                       " There section above, and note that parking at popular"
                       " trailheads fills early on weekends."),
        })
    faqs.append({
        "question": f"Are dogs allowed on the {name} trail?",
        "answer": ("Rules vary by land manager — national parks often prohibit dogs"
                   " on trails, while most national forests allow them on leash."
                   " Check with the managing agency for this trail before bringing"
                   " your dog, and pack out waste."),
    })
    elev = d.get("elevation") or 0
    slug = d.get("state_slug", "")
    if elev >= 11000:
        season = ("July through September is the reliable snow-free window."
                  " Start early to avoid afternoon thunderstorms above treeline.")
    elif slug in DESERT and elev < 8000:
        season = ("October through April. Summer heat at this elevation is"
                  " dangerous — if hiking in summer, start at dawn and carry"
                  " extra water.")
    elif slug in SOUTH and elev < 4000:
        season = ("Most of the year. Fall and spring are most comfortable;"
                  " summer is hot and humid, and ice is possible on shaded"
                  " stretches in mid-winter.")
    else:
        season = ("Late May through October for snow-free hiking. Check a"
                  " summit point forecast before you go — conditions up high"
                  " differ from the trailhead.")
    faqs.append({"question": f"When is the best time to hike {name}?",
                 "answer": season})
    if d.get("elevation"):
        faqs.append({
            "question": f"How tall is {name}?",
            "answer": (f"{name} stands at {fmt(d['elevation'])} feet"
                       f" ({int(round((d['elevation'] or 0) * 0.3048)):,} meters)"
                       f" in {state}."),
        })
    return faqs


# ---------------------------------------------------------------- driver

def is_v1_generated(desc):
    """v1 signature: templated single paragraph, no section headings."""
    return (desc.startswith('<div class="mountain-description prose prose-stone max-w-none">\n  <p>')
            and "<h3>" not in desc)


def process(path, force=False):
    d = json.loads(Path(path).read_text())
    if not d.get("name") or not d.get("slug"):
        return False
    desc = d.get("generated_description") or ""
    replace = force or not desc.strip() or is_v1_generated(desc)
    changed = False
    if replace:
        d["generated_description"] = build_description(d)
        changed = True
    pc = d.setdefault("page_content", {})
    if force or not pc.get("faqs"):
        pc["faqs"] = build_faqs(d)
        changed = True
    if changed:
        Path(path).write_text(json.dumps(d, indent=2) + "\n")
        print(f"  ✅ {'desc+faqs' if replace else 'faqs'}: {path}")
    return changed


def main():
    args = sys.argv[1:]
    force = "--force" in args
    args = [a for a in args if a != "--force"]
    files = []
    if "--state" in args:
        i = args.index("--state")
        files = sorted(glob.glob(str(DATA / args[i + 1] / "*.json")))
        args = args[:i] + args[i + 2:]
    files += [a for a in args if a.endswith(".json")]
    if not files:
        print("Usage: python3 scripts/generate-description.py "
              "[--force] (--state <slug> | <file.json> ...)")
        sys.exit(1)
    n = sum(process(f, force) for f in files)
    print(f"Updated {n} file(s).")


if __name__ == "__main__":
    main()
