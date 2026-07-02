#!/usr/bin/env python3
"""
Normalize every trail JSON to one canonical, self-consistent schema.

The dataset grew in layers: hand-authored fields (trails[].distance_miles /
elevation_gain, sourced from official guides) and machine-computed fields
(trails[].stats.distance / gain, derived from GPS paths — some of which were
synthetic and produced garbage like gain=9 ft on a 2,000-ft climb). The
frontend reads both depending on component, so the same trail could show two
different distances. That is a trust bug.

Reconciliation rule per route:
  * both present, divergence > 25%  → the GPS-computed value is the suspect
    one (bad/synthetic path); adopt the AUTHORED value into stats.* and flag
    the route in the report for path review.
  * both present, divergence small  → keep stats.* (GPS precision) and sync
    the legacy field to it, so every component shows the same number.
  * only one present               → copy it to the other.
Also syncs difficulty between trail.difficulty and stats.difficulty.

Canonical read order for the frontend is stats.* (legacy fields are kept in
sync for backwards compatibility). Writes a report of every change to
pipeline-reports/normalize-report.json.

Usage:
  python3 scripts/normalize-schema.py            # all states, report + fix
  python3 scripts/normalize-schema.py --dry-run  # report only
  python3 scripts/normalize-schema.py --state vermont
"""

import glob
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "website" / "src" / "data"
NON_TRAIL = {"blog", "guides", "_rejected"}
DIVERGENCE = 0.25  # >25% apart → computed value considered corrupt


def reconcile(authored, computed):
    """Return (value, source) for a stat with both representations."""
    if authored is None and computed is None:
        return None, None
    if authored is None:
        return computed, "computed"
    if computed is None:
        return authored, "authored"
    base = max(abs(authored), abs(computed), 1e-9)
    if abs(authored - computed) / base > DIVERGENCE:
        return authored, "authored (computed diverged)"
    return computed, "computed"


def normalize_route(t):
    """Normalize one route dict in place; return list of change notes."""
    changes = []
    stats = t.setdefault("stats", {})

    for legacy_key, stat_key, unit in (("distance_miles", "distance", "mi"),
                                       ("elevation_gain", "gain", "ft")):
        authored = t.get(legacy_key)
        computed = stats.get(stat_key)
        value, source = reconcile(authored, computed)
        if value is None:
            continue
        if stats.get(stat_key) != value:
            changes.append(f"stats.{stat_key}: {computed} → {value} {unit} "
                           f"[{source}]")
            stats[stat_key] = value
        if legacy_key in t and t[legacy_key] != value:
            changes.append(f"{legacy_key}: {authored} → {value} {unit} [synced]")
            t[legacy_key] = value

    # difficulty: one truth, mirrored in both places the frontend reads.
    diff = t.get("difficulty") or stats.get("difficulty")
    if diff:
        if t.get("difficulty") != diff:
            t["difficulty"] = diff
            changes.append(f"difficulty → {diff} [synced]")
        if stats.get("difficulty") != diff:
            stats["difficulty"] = diff
            changes.append(f"stats.difficulty → {diff} [synced]")
    return changes


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]
    states = None
    if "--state" in args:
        i = args.index("--state")
        states = [args[i + 1]]
    if states is None:
        states = sorted(p.name for p in DATA.iterdir()
                        if p.is_dir() and p.name not in NON_TRAIL)

    report = {"date": str(date.today()), "dry_run": dry, "files": {}}
    files_changed = routes_flagged = 0

    for state in states:
        for f in sorted(glob.glob(str(DATA / state / "*.json"))):
            d = json.loads(Path(f).read_text())
            if not d.get("name"):
                continue
            all_changes = []
            for idx, t in enumerate(d.get("trails") or []):
                notes = normalize_route(t)
                if notes:
                    label = t.get("name") or f"route {idx + 1}"
                    all_changes.append({"route": label, "changes": notes})
                    if any("diverged" in n for n in notes):
                        routes_flagged += 1
            # trails_config mirrors trails on older files — keep it consistent
            # (some components fall back to it).
            if "trails_config" in d and all_changes:
                for tc, t in zip(d.get("trails_config") or [],
                                 d.get("trails") or []):
                    s = t.get("stats") or {}
                    if "distance_miles" in tc and s.get("distance") is not None:
                        tc["distance_miles"] = s["distance"]
                    if "elevation_gain" in tc and s.get("gain") is not None:
                        tc["elevation_gain"] = s["gain"]
            if all_changes:
                files_changed += 1
                rel = f.split("data/")[-1]
                report["files"][rel] = all_changes
                if not dry:
                    Path(f).write_text(json.dumps(d, indent=2) + "\n")

    out = ROOT / "pipeline-reports" / "normalize-report.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")

    print(f"{'DRY RUN — ' if dry else ''}Normalized {files_changed} file(s); "
          f"{routes_flagged} route(s) had corrupt computed stats replaced by "
          f"authored values (path review recommended).")
    print(f"Full change log: pipeline-reports/normalize-report.json")


if __name__ == "__main__":
    main()
