#!/usr/bin/env python3
"""
Generate a unique, factual description paragraph per trail from its real fields.

Every sentence is built only from data already in the file (name, elevation,
state, prominence, route stats, nearby peaks, data source). Nothing is
embellished or invented — no "stunning views" or "best hike" claims. Opening
phrasing is varied deterministically by slug so pages don't read as
duplicate/boilerplate content (which would hurt SEO).

Idempotent: trails that already have a non-empty generated_description are left
untouched unless --force is passed — so hand-written descriptions on curated
states are never overwritten.

Usage:
  python3 scripts/generate-description.py <file.json> [<file.json> ...]
  python3 scripts/generate-description.py --state new-jersey   # whole state
  python3 scripts/generate-description.py --force <file.json>
"""

import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "website" / "src" / "data"


def feature_word(name):
    n = name.lower()
    if "falls" in n or "cascade" in n:
        return "waterfall"
    if "lake" in n or "pond" in n:
        return "destination"
    if "gorge" in n or "canyon" in n:
        return "gorge"
    return "summit"


def fmt(n):
    try:
        return f"{int(round(float(n))):,}"
    except (TypeError, ValueError):
        return None


def primary_route(d):
    trails = d.get("trails") or []
    if not trails:
        return {}
    return max(trails, key=lambda t: (t.get("stats") or {}).get("distance", 0) or 0)


def opening(d):
    """Lead sentence, varied deterministically by slug to avoid boilerplate."""
    name = d["name"]
    state = d.get("state", "")
    fw = feature_word(name)
    elev = fmt(d.get("elevation"))
    variants = []
    if elev:
        variants = [
            f"<strong>{name}</strong> is a {elev}-foot {fw} in {state}.",
            f"At {elev} feet, <strong>{name}</strong> is a {fw} in {state}.",
            f"<strong>{name}</strong> rises to {elev} feet in {state}.",
        ]
    else:
        variants = [
            f"<strong>{name}</strong> is a hiking {fw} in {state}.",
            f"<strong>{name}</strong> is located in {state}.",
        ]
    idx = sum(ord(c) for c in d.get("slug", name)) % len(variants)
    return variants[idx]


def prominence_clause(d):
    prom = (d.get("osm") or {}).get("prominence_m")
    if not prom:
        return ""
    try:
        ft = int(round(float(prom) * 3.28084))
        return f" It has roughly {ft:,} feet of topographic prominence."
    except (TypeError, ValueError):
        return ""


def route_clause(d):
    t = primary_route(d)
    stats = t.get("stats") or {}
    dist = stats.get("distance")
    gain = stats.get("gain")
    diff = t.get("difficulty") or stats.get("difficulty")
    typ = t.get("type") or stats.get("type")
    time = stats.get("time")
    rname = t.get("name")
    if not (dist or gain or diff):
        return ""  # imported stub with no route facts yet
    parts = []
    lead = f"The {rname}" if rname else "The main route"
    if dist:
        seg = f"{lead} is a {dist}-mile"
        if typ:
            seg += f" {typ.lower()}"
        seg += " hike"
    else:
        seg = f"{lead} is a hike"
    if gain:
        seg += f" with about {fmt(gain)} feet of elevation gain"
    if diff:
        seg += f", rated {diff}"
    seg += "."
    parts.append(seg)
    if time:
        parts.append(f" Plan for roughly {time} hours round trip.")
    return " " + "".join(parts)


def nearby_clause(d):
    peaks = [p.get("name") for p in (d.get("nearby_peaks") or []) if p.get("name")]
    if not peaks:
        return ""
    peaks = peaks[:3]
    if len(peaks) == 1:
        joined = peaks[0]
    else:
        joined = ", ".join(peaks[:-1]) + f" and {peaks[-1]}"
    return f" Nearby peaks include {joined}."


def source_clause(d):
    by = (d.get("data_sources") or {}).get("verified_by", "")
    by = by.split(" — ")[0].strip()  # drop the "UPDATE before enabling" suffix
    if not by:
        return (" Verify current conditions with the official land manager "
                "before you go.")
    return (f" Trail data is sourced from {by}; verify current conditions with "
            "the official land manager before you go.")


def build_description(d):
    body = (opening(d) + prominence_clause(d) + route_clause(d)
            + nearby_clause(d) + source_clause(d))
    return f'<div class="mountain-description prose prose-stone max-w-none">\n  <p>{body}</p>\n</div>'


def process(path, force=False):
    d = json.loads(Path(path).read_text())
    if not d.get("name"):
        print(f"  · skip (no name): {path}")
        return False
    if d.get("generated_description") and not force:
        return False
    d["generated_description"] = build_description(d)
    Path(path).write_text(json.dumps(d, indent=2) + "\n")
    print(f"  ✅ description: {path}")
    return True


def main():
    args = sys.argv[1:]
    force = "--force" in args
    args = [a for a in args if a != "--force"]
    files = []
    if "--state" in args:
        i = args.index("--state")
        state = args[i + 1]
        files = sorted(glob.glob(str(DATA / state / "*.json")))
        args = args[:i] + args[i + 2:]
    files += [a for a in args if a.endswith(".json")]
    if not files:
        print("Usage: python3 scripts/generate-description.py "
              "[--force] (--state <slug> | <file.json> ...)")
        sys.exit(1)
    n = sum(process(f, force) for f in files)
    print(f"Wrote {n} description(s).")


if __name__ == "__main__":
    main()
