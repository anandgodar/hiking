#!/usr/bin/env python3
"""
Curate a state's imported peaks down to real hiking destinations.

OpenStreetMap returns every named bump (a state can have 1000+), so a raw
import is mostly noise — minor hills with no prominence, no Wikidata entry, and
generic names. Publishing all of them creates thin, near-duplicate pages that
hurt SEO. This tool ranks each imported trail by real notability signals and
sets the low-signal ones aside so you enrich only the genuine destinations.

Notability score (higher = more likely a real destination):
  * prominence (metres)         — the standard mountaineering metric
  * has a Wikidata/Wikipedia entry — strong signal of a notable place
  * elevation                   — mild tiebreaker
  * generic name penalty        — "...Hill", duplicate "South Peak" style names

Reversible: --apply MOVES rejects to website/src/data/_rejected/<state>/ (it
never deletes), so you can pull any back. Hand-curated files (no `osm` block,
i.e. not imported) are always kept and never touched.

Usage:
  python3 scripts/curate-state.py <state>                 # report only
  python3 scripts/curate-state.py <state> --keep-top 15   # keep 15 best
  python3 scripts/curate-state.py <state> --min-prominence 150
  python3 scripts/curate-state.py <state> --keep-top 15 --apply
"""

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "website" / "src" / "data"

GENERIC_NAME = re.compile(r"\b(hill|knob|rise|ridge|mound)\b", re.I)


def prominence_m(rec):
    raw = (rec.get("osm") or {}).get("prominence_m")
    if not raw:
        return None
    m = re.match(r"[-+]?[0-9]*\.?[0-9]+", str(raw))
    return float(m.group()) if m else None


def notability(rec):
    """Composite score; None prominence is treated as 0 but flagged separately."""
    score = 0.0
    prom = prominence_m(rec)
    if prom is not None:
        score += prom                      # metres of prominence dominate
    if (rec.get("osm") or {}).get("wikidata"):
        score += 300                       # notable enough to have a Wikidata id
    elev = rec.get("elevation") or 0
    score += elev / 100.0                  # mild tiebreaker
    if GENERIC_NAME.search(rec.get("name", "")):
        score -= 100                       # generic "Hill"/"Knob" style names
    return score


def load(state):
    items = []
    for f in sorted((DATA / state).glob("*.json")):
        try:
            rec = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue
        items.append((f, rec))
    return items


def main():
    args = sys.argv[1:]
    opts = {"keep_top": None, "min_prominence": None, "apply": False}
    pos = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--keep-top":
            opts["keep_top"] = int(args[i + 1]); i += 2
        elif a == "--min-prominence":
            opts["min_prominence"] = float(args[i + 1]); i += 2
        elif a == "--apply":
            opts["apply"] = True; i += 1
        else:
            pos.append(a); i += 1

    if len(pos) != 1:
        sys.exit("Usage: python3 scripts/curate-state.py <state> "
                 "[--keep-top N | --min-prominence M] [--apply]")
    state = pos[0]
    state_dir = DATA / state
    if not state_dir.is_dir():
        sys.exit(f"❌ No data folder for '{state}'")

    items = load(state)
    # Hand-curated (non-imported) files are always kept and never ranked out.
    imported = [(f, r) for f, r in items if r.get("osm")]
    handmade = [(f, r) for f, r in items if not r.get("osm")]

    ranked = sorted(imported, key=lambda fr: notability(fr[1]), reverse=True)

    keep, cut = [], []
    for rank, (f, r) in enumerate(ranked):
        prom = prominence_m(r)
        is_keep = True
        if opts["min_prominence"] is not None:
            is_keep = prom is not None and prom >= opts["min_prominence"]
        if opts["keep_top"] is not None:
            is_keep = rank < opts["keep_top"]
        if opts["min_prominence"] is None and opts["keep_top"] is None:
            # Default heuristic: keep peaks with real prominence or a Wikidata id.
            is_keep = (prom is not None and prom >= 100) or bool((r.get("osm") or {}).get("wikidata"))
        (keep if is_keep else cut).append((f, r, prom))

    print(f"State: {state}")
    print(f"  hand-curated kept untouched: {len(handmade)}")
    print(f"  imported: {len(imported)}  →  keep {len(keep)}, cut {len(cut)}")
    print("\n  KEEP (top by notability):")
    for f, r, prom in keep[:30]:
        print(f"    ✓ {r['name']:<30} {r.get('elevation','?')} ft  "
              f"prom={prom if prom is not None else '-'}m  "
              f"wiki={'y' if (r.get('osm') or {}).get('wikidata') else '-'}")
    if cut:
        print(f"\n  CUT (low signal, {len(cut)} — sample):")
        for f, r, prom in cut[:15]:
            print(f"    ✗ {r['name']:<30} {r.get('elevation','?')} ft  "
                  f"prom={prom if prom is not None else '-'}m")

    if not opts["apply"]:
        print("\n  (report only — re-run with --apply to move CUT files to "
              "_rejected/)")
        return

    rej_dir = DATA / "_rejected" / state
    rej_dir.mkdir(parents=True, exist_ok=True)
    for f, r, prom in cut:
        shutil.move(str(f), str(rej_dir / f.name))
    print(f"\n✅ Moved {len(cut)} file(s) to website/src/data/_rejected/{state}/ "
          f"(reversible). Kept {len(keep) + len(handmade)}.")
    print(f"   Re-run: python3 scripts/run-pipeline.py --state {state}")


if __name__ == "__main__":
    main()
