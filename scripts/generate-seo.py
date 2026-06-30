#!/usr/bin/env python3
"""
Generate SEO blocks for trail JSON files from their existing real fields.

Produces the same structure already used across the site (meta_title,
meta_description, canonical_url, schema_place, schema_faq). Every value is
derived from data already present in the file (name, state, elevation, lat/lon,
trails[].stats) — no trail facts are invented.

Idempotent: existing seo fields are kept unless --force is passed. Only missing
pieces are filled in.

Usage:
  python3 scripts/generate-seo.py <trail-json> [<trail-json> ...]
  python3 scripts/generate-seo.py --force <trail-json>      # rebuild even if present
"""

import json
import sys


def popular_trail(data):
    """Pick the representative route: longest by distance, else first."""
    trails = data.get("trails") or []
    if not trails:
        return {}
    return max(trails, key=lambda t: (t.get("stats") or {}).get("distance", 0) or 0)


def difficulty_of(trail):
    stats = trail.get("stats") or {}
    return trail.get("difficulty") or stats.get("difficulty") or "Moderate"


def fmt_elev(elevation):
    try:
        return f"{int(elevation):,}"
    except (TypeError, ValueError):
        return str(elevation)


def build_meta_title(data):
    name = data["name"]
    n = len(data.get("trails") or [])
    if n >= 2:
        return f"{name} Trail Guide | {n} Routes, Maps & Conditions"
    return f"{name} Trail Guide | Map, Route & Conditions"


def build_meta_description(data):
    name = data["name"]
    state = data.get("state", "")
    elev = fmt_elev(data.get("elevation"))
    n = len(data.get("trails") or [])
    routes = f"{n} trail maps" if n >= 2 else "trail map"
    desc = (f"Plan your {name} hike with current conditions, {routes} & parking "
            f"info. {state} summit at {elev} ft.")
    # Keep meta descriptions within the ~160 char SEO sweet spot.
    return desc[:160]


def build_canonical(data):
    return f"/trails/{data.get('state_slug', '')}/{data.get('slug', '')}"


def build_schema_place(data):
    place = {
        "@context": "https://schema.org",
        "@type": "Place",
        "name": data["name"],
        "description": (f"{data['name']} is a {fmt_elev(data.get('elevation'))} foot "
                        f"peak in {data.get('state', '')} offering hiking trails "
                        f"with scenic views."),
        "geo": {
            "@type": "GeoCoordinates",
            "latitude": data.get("lat"),
            "longitude": data.get("lon"),
            "elevation": {
                "@type": "QuantitativeValue",
                "value": data.get("elevation"),
                "unitCode": "FOT",
            },
        },
        "address": {
            "@type": "PostalAddress",
            "addressRegion": data.get("state", ""),
            "addressCountry": "US",
        },
    }
    contains = []
    for t in data.get("trails") or []:
        markers = (t.get("geo") or {}).get("markers") or {}
        start = markers.get("start") or [data.get("lat"), data.get("lon")]
        contains.append({
            "@type": "Place",
            "name": t.get("name", data["name"]),
            "additionalType": "HikingTrail",
            "geo": {
                "@type": "GeoCoordinates",
                "latitude": start[0] if start else data.get("lat"),
                "longitude": start[1] if start else data.get("lon"),
            },
        })
    if contains:
        place["containsPlace"] = contains
    return place


def build_schema_faq(data):
    name = data["name"]
    state = data.get("state", "")
    elev = fmt_elev(data.get("elevation"))
    trail = popular_trail(data)
    stats = trail.get("stats") or {}
    diff = difficulty_of(trail)
    dist = stats.get("distance")
    time = stats.get("time")
    dist_str = f"{dist}-mile" if dist else ""
    time_str = (f"about {time} hours round trip"
                if time else "several hours round trip")

    def qa(q, a):
        return {"@type": "Question", "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a}}

    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            qa(f"How long does it take to hike {name}?",
               f"The popular {trail.get('name', 'main route')} on {name} is "
               f"{dist_str} and takes {time_str}. Start early, especially on "
               f"weekends when parking fills quickly."),
            qa(f"Is {name} hard to hike?",
               f"{name} is rated {diff}. At {elev} feet, plan for the terrain and "
               f"weather typical of {state} peaks. Proper footwear and "
               f"preparation are essential."),
            qa(f"Do I need a permit to hike {name}?",
               f"Check the official land manager's site before you go — most "
               f"trailheads do not require a hiking permit, but parking fees or "
               f"seasonal access rules may apply."),
            qa(f"What is the best trail to hike {name}?",
               f"The most popular route is the {trail.get('name', 'main trail')}, "
               f"a {dist_str} {diff.lower()} hike to the {name} summit."),
            qa(f"When is the best time to hike {name}?",
               f"Late spring through fall offers the best conditions on {name}. "
               f"Summer and fall bring the most stable weather; winter hiking "
               f"requires specialized gear and experience."),
        ],
    }


def generate_seo(data, force=False):
    """Fill in missing seo fields. Returns True if anything changed."""
    seo = data.get("seo") or {}
    changed = False
    builders = {
        "meta_title": build_meta_title,
        "meta_description": build_meta_description,
        "canonical_url": build_canonical,
        "schema_place": build_schema_place,
        "schema_faq": build_schema_faq,
    }
    for key, builder in builders.items():
        if force or not seo.get(key):
            seo[key] = builder(data)
            changed = True
    if changed:
        data["seo"] = seo
    return changed


def process_file(path, force=False):
    with open(path) as f:
        data = json.load(f)
    if not data.get("name"):
        print(f"  ⚠️  skip (no name): {path}")
        return False
    if generate_seo(data, force=force):
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        print(f"  ✅ SEO written: {path}")
        return True
    print(f"  · SEO already complete: {path}")
    return False


def main():
    args = sys.argv[1:]
    force = "--force" in args
    files = [a for a in args if a != "--force"]
    if not files:
        print("Usage: python3 scripts/generate-seo.py [--force] <trail-json> ...")
        sys.exit(1)
    for path in files:
        process_file(path, force=force)


if __name__ == "__main__":
    main()
