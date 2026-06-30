#!/usr/bin/env python3
"""
Internal link-integrity check for trail data.

Every `nearby_peaks[]` entry becomes a clickable internal link on the site
(/<state_slug>/hikes/<slug>). If the target trail file doesn't exist, that link
404s — silently hurting retention (dead clicks) and SEO (broken internal links,
orphaned crawl paths). This script verifies each link resolves to a real trail
file, and flags hikes with no internal links at all (thin connectivity).

A trail page exists iff its data file exists at
website/src/data/<state_slug>/<slug>.json, so file existence is the correct
proxy for "the link works".

Usage:
  python3 scripts/check-links.py                     # all trail states
  python3 scripts/check-links.py new-hampshire maine # only these states
Exit code: 0 if no broken links, 1 if any broken link is found.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def trail_states():
    """State slugs from pipeline.config.json (single source of truth)."""
    cfg = ROOT / "pipeline.config.json"
    if cfg.exists():
        slugs = [s["slug"] for s in json.loads(cfg.read_text()).get("states", [])]
        if slugs:
            return slugs
    data_dir = ROOT / "website" / "src" / "data"
    skip = {"blog", "guides"}
    return [p.name for p in data_dir.iterdir() if p.is_dir() and p.name not in skip]


def build_index(states):
    """Set of (state_slug, slug) for every existing trail file."""
    index = set()
    data_dir = ROOT / "website" / "src" / "data"
    for state in states:
        for f in (data_dir / state).glob("*.json"):
            try:
                d = json.loads(f.read_text())
            except json.JSONDecodeError:
                continue
            index.add((d.get("state_slug", state), d.get("slug", f.stem)))
    return index


def check(states):
    index = build_index(trail_states())  # validate against ALL states
    data_dir = ROOT / "website" / "src" / "data"
    broken = []       # (file, name, target_state, target_slug)
    no_links = []     # files with zero nearby_peaks
    total_links = 0

    for state in states:
        for f in sorted((data_dir / state).glob("*.json")):
            try:
                d = json.loads(f.read_text())
            except json.JSONDecodeError:
                continue
            peaks = d.get("nearby_peaks") or []
            if not peaks:
                no_links.append(f.relative_to(ROOT))
                continue
            for np in peaks:
                total_links += 1
                tgt = (np.get("state_slug") or d.get("state_slug"), np.get("slug"))
                if tgt not in index:
                    broken.append((f.relative_to(ROOT), np.get("name", "?"),
                                   tgt[0], tgt[1]))
    return broken, no_links, total_links


def main():
    states = sys.argv[1:] or trail_states()
    broken, no_links, total = check(states)

    print(f"Internal links checked: {total} nearby_peaks across "
          f"{len(states)} state(s)")

    if no_links:
        print(f"\n⚠️  {len(no_links)} hike(s) have NO nearby_peaks "
              f"(weak internal linking / retention):")
        for f in no_links[:20]:
            print(f"     · {f}")

    if broken:
        print(f"\n❌ {len(broken)} BROKEN internal link(s) "
              f"(target trail file does not exist):")
        for f, name, st, slug in broken:
            print(f"     · {f}  →  {st}/{slug}  ('{name}')")
        print("\n   Fix: correct the slug/state_slug, or add the missing trail file.")
        return 1

    print("✅ All internal nearby_peaks links resolve to real trail pages.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
