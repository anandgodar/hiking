#!/usr/bin/env python3
"""
One-time backfill of explicit distance semantics onto existing trail records.

Adds `route_length_mi`, `distance_type` and `distance_source` to every trail
with geometry, and corrects `distance` to the HIKED distance (twice the
geometry for out-and-back routes) — see scripts/route_metrics.py for the rule.

Difficulty and time are then recomputed from the corrected distance, because
both were derived from the understated one-way value. Difficulty is only
recomputed for records whose difficulty was computed in the first place;
authored distances are preserved and marked, never overwritten.

Usage:
  python3 scripts/migrate-distance-semantics.py --dry-run
  python3 scripts/migrate-distance-semantics.py
  python3 scripts/migrate-distance-semantics.py --state colorado
"""

import glob
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "website" / "src" / "data"
sys.path.insert(0, str(ROOT / "scripts"))
import route_metrics as rm  # noqa: E402


def compute_difficulty(distance, gain):
    """NPS/Shenandoah numerical rating — same formula as curate-state.py."""
    if not distance or not gain or distance <= 0 or gain <= 0:
        return None
    r = math.sqrt(2 * gain * distance)
    if r < 50:
        return "Easy"
    if r < 100:
        return "Moderate"
    if r < 150:
        return "Hard"
    return "Strenuous"


def naismith_hours(distance, gain):
    if not distance:
        return None
    return round(max(0.5, distance / 3 + (gain or 0) / 2000) * 2) / 2


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    state = None
    if "--state" in args:
        state = args[args.index("--state") + 1]
    pattern = str(DATA / (state or "*") / "*.json")

    changed = rebanded = authored = 0
    band_moves = []
    for p in sorted(glob.glob(pattern)):
        try:
            d = json.loads(Path(p).read_text())
        except Exception:
            continue
        if not isinstance(d, dict) or not d.get("state_slug"):
            continue
        touched = False
        for t in (d.get("trails") or []):
            stats = t.get("stats") or {}
            before_dist = stats.get("distance")
            before_diff = t.get("difficulty") or stats.get("difficulty")
            if not rm.apply_to_trail(t):
                continue
            touched = True
            stats = t["stats"]
            if stats.get("distance_source") == "authored":
                authored += 1
                continue
            new_diff = compute_difficulty(stats.get("distance"), stats.get("gain"))
            if new_diff:
                if before_diff and new_diff != before_diff:
                    rebanded += 1
                    band_moves.append((d["name"], before_diff, new_diff,
                                       before_dist, stats["distance"]))
                t["difficulty"] = stats["difficulty"] = new_diff
            hours = naismith_hours(stats.get("distance"), stats.get("gain"))
            if hours:
                stats["time"] = hours
        if touched:
            changed += 1
            if not dry:
                Path(p).write_text(json.dumps(d, indent=2) + "\n")

    print(f"{'[dry-run] ' if dry else ''}records updated: {changed}")
    print(f"  authored distances preserved (geometry incomplete): {authored}")
    print(f"  difficulty re-banded after distance correction: {rebanded}")
    for name, a, b, da, db in band_moves[:15]:
        print(f"    {name[:28]:30} {a:>9} -> {b:<9} ({da} -> {db} mi)")


if __name__ == "__main__":
    main()
