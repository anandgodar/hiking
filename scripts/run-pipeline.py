#!/usr/bin/env python3
"""
Trail-data pipeline orchestrator.

One command to (re)build and quality-check trail data per state, driven by
pipeline.config.json. Everything runs LOCALLY and only writes to
website/src/data/<state>/. Deployment stays manual: once the pipeline reports
PASS for a state, copy that state's JSON files to the web host yourself.

Per state, for each target state the orchestrator runs:
  1. (optional) GPS generation  - prefers a real .gpx (accurate/reliable);
                                   falls back to synthetic + flags it
  2. GPS quality audit          - reuses scripts/audit-gps-quality.py
  3. Trail-data validation      - reuses scripts/validate-trail-data.js

Usage:
  python3 scripts/run-pipeline.py                # all enabled states (audit+validate)
  python3 scripts/run-pipeline.py --rerun        # only states with "rerun": true
  python3 scripts/run-pipeline.py --state maine  # one state, ignores enabled/rerun
  python3 scripts/run-pipeline.py --no-validate  # skip the JS validation step
"""

import argparse
import importlib.util
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def load_module(path, name):
    """Load a script with a hyphenated filename as an importable module."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_config():
    cfg_path = ROOT / "pipeline.config.json"
    if not cfg_path.exists():
        sys.exit(f"❌ Config not found: {cfg_path}")
    return json.loads(cfg_path.read_text())


def select_states(config, args):
    states = config.get("states", [])
    if args.state:
        chosen = [s for s in states if s["slug"] == args.state]
        if not chosen:
            sys.exit(f"❌ State '{args.state}' not found in pipeline.config.json")
        return chosen
    enabled = [s for s in states if s.get("enabled", True)]
    if args.rerun:
        return [s for s in enabled if s.get("rerun", False)]
    return enabled


def generate_gps(state, config, audit_mod):
    """Build geo data for trails missing it. Prefer real GPX, flag synthetic."""
    data_dir = ROOT / config["data_dir"] / state["slug"]
    gpx_dir = ROOT / config.get("gpx_dir", "gpx-downloads")
    synthetic = []
    for trail_file in sorted(data_dir.glob("*.json")):
        try:
            data = json.loads(trail_file.read_text())
        except json.JSONDecodeError:
            continue
        trails = data.get("trails") or []
        has_geo = trails and trails[0].get("geo", {}).get("path")
        if has_geo:
            continue
        slug = data.get("slug", trail_file.stem)
        gpx = gpx_dir / f"{slug}.gpx"
        if gpx.exists():
            # Accurate path from a real GPX track.
            subprocess.run(
                [sys.executable, str(SCRIPTS / "gpx-to-geo.py"), str(gpx), str(trail_file)],
                check=False,
            )
        elif state.get("synthetic_fallback", False):
            # No GPX available: interpolate so the page renders, then flag it.
            subprocess.run(
                [sys.executable, str(SCRIPTS / "enhance-gps-path.py"), str(trail_file)],
                check=False,
            )
            synthetic.append(slug)
    return synthetic


def generate_seo(state, config):
    """Fill missing SEO blocks (meta, canonical, schema) from real fields."""
    data_dir = ROOT / config["data_dir"] / state["slug"]
    updated = []
    for trail_file in sorted(data_dir.glob("*.json")):
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "generate-seo.py"), str(trail_file)],
            capture_output=True, text=True,
        )
        if "SEO written" in proc.stdout:
            updated.append(trail_file.stem)
    return updated


def generate_nearby(state, config):
    """Fill nearby_peaks (nearest in-state trails) for hikes that have none."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "generate-nearby-peaks.py"), state["slug"]],
        capture_output=True, text=True,
    )
    return [ln for ln in proc.stdout.splitlines() if ln.strip().startswith("✅")]


def audit_state(state, config, audit_mod):
    """Per-state GPS quality audit using the shared audit logic."""
    data_dir = ROOT / config["data_dir"] / state["slug"]
    min_score = config.get("quality", {}).get("min_score", 80)
    results = []
    for trail_file in sorted(data_dir.glob("*.json")):
        r = audit_mod.audit_trail(str(trail_file))
        r["state_slug"] = state["slug"]
        results.append(r)
    passed = [r for r in results if r.get("quality_score", 0) >= min_score]
    failed = [r for r in results if r.get("quality_score", 0) < min_score]
    return results, passed, failed


def main():
    parser = argparse.ArgumentParser(description="Trail-data pipeline orchestrator")
    parser.add_argument("--rerun", action="store_true", help="only states with rerun:true")
    parser.add_argument("--state", help="process a single state by slug")
    parser.add_argument("--no-validate", action="store_true", help="skip JS validation")
    args = parser.parse_args()

    config = load_config()
    audit_mod = load_module(SCRIPTS / "audit-gps-quality.py", "audit_gps_quality")
    links_mod = load_module(SCRIPTS / "check-links.py", "check_links")

    targets = select_states(config, args)
    if not targets:
        print("No states selected. Tip: set \"rerun\": true in pipeline.config.json, "
              "or pass --state <slug>.")
        return 0

    report_dir = ROOT / config.get("report_dir", "pipeline-reports")
    report_dir.mkdir(exist_ok=True)
    min_score = config.get("quality", {}).get("min_score", 80)

    print("=" * 78)
    print(f"TRAIL-DATA PIPELINE  ·  {date.today()}  ·  {len(targets)} state(s)")
    print("=" * 78)

    overall = {"states": [], "all_pass": True}

    for state in targets:
        slug = state["slug"]
        print(f"\n▶ {slug}")

        synthetic = []
        if state.get("generate_gps", False):
            print("  · generating GPS (prefer real GPX, fall back to synthetic)…")
            synthetic = generate_gps(state, config, audit_mod)
            if synthetic:
                print(f"  · {len(synthetic)} trail(s) used SYNTHETIC paths "
                      f"(flagged for real-GPX upgrade)")

        if state.get("generate_nearby", True):
            linked = generate_nearby(state, config)
            if linked:
                print(f"  · nearby_peaks: linked {len(linked)} hike(s) that had none")

        if state.get("generate_seo", True):
            seo_updated = generate_seo(state, config)
            if seo_updated:
                print(f"  · SEO: filled {len(seo_updated)} trail(s) missing meta/schema")

        # Internal link integrity: broken nearby_peaks links 404 → retention/SEO loss.
        broken_links, no_links, total_links = links_mod.check([slug])
        if broken_links:
            print(f"  · links: {len(broken_links)} BROKEN nearby_peaks link(s)")
            for f, name, st, tslug in broken_links[:10]:
                print(f"      ✗ {f}  →  {st}/{tslug}")
        elif no_links:
            print(f"  · links: {total_links} ok, "
                  f"{len(no_links)} hike(s) have no nearby_peaks (weak linking)")
        else:
            print(f"  · links: {total_links} nearby_peaks all resolve ✓")

        results, passed, failed = audit_state(state, config, audit_mod)
        state_pass = len(failed) == 0 and len(broken_links) == 0
        overall["all_pass"] = overall["all_pass"] and state_pass

        print(f"  · audit: {len(passed)}/{len(results)} trails ≥ {min_score} "
              f"→ {'PASS' if state_pass else 'NEEDS WORK'}")
        for r in sorted(failed, key=lambda x: x.get("quality_score", 0))[:10]:
            st = r.get("stats", {})
            print(f"      ✗ {r['name']:<32} score {r.get('quality_score', 0):>3} "
                  f"({st.get('points_per_mile', 0)} pts/mi)")

        report = {
            "state": slug,
            "date": str(date.today()),
            "min_score": min_score,
            "total": len(results),
            "passed": len(passed),
            "failed": len(failed),
            "synthetic_gps": synthetic,
            "broken_links": [
                {"file": str(f), "target": f"{st}/{tslug}", "name": name}
                for f, name, st, tslug in broken_links
            ],
            "hikes_without_nearby_peaks": [str(f) for f in no_links],
            "needs_work": [
                {"name": r["name"], "file": r.get("file"),
                 "score": r.get("quality_score", 0),
                 "issues": r.get("issues", []), "warnings": r.get("warnings", [])}
                for r in failed
            ],
        }
        (report_dir / f"{slug}.json").write_text(json.dumps(report, indent=2))
        overall["states"].append(report)

    # Whole-repo schema/field validation (JS).
    validate_ok = True
    if not args.no_validate:
        print("\n" + "-" * 78)
        print("Running trail-data validation (node scripts/validate-trail-data.js)…")
        proc = subprocess.run(
            ["node", str(SCRIPTS / "validate-trail-data.js")], cwd=str(ROOT)
        )
        validate_ok = proc.returncode == 0

    print("\n" + "=" * 78)
    print("SUMMARY")
    print("=" * 78)
    for s in overall["states"]:
        parts = []
        if s["failed"]:
            parts.append(f"{s['failed']} need work")
        if s["broken_links"]:
            parts.append(f"{len(s['broken_links'])} broken links")
        if s["synthetic_gps"]:
            parts.append(f"{len(s['synthetic_gps'])} synthetic")
        flag = ", ".join(parts) if parts else "PASS"
        print(f"  {s['state']:<16} {s['passed']}/{s['total']} ≥ {min_score}  [{flag}]")
    print(f"\n  Validation: {'PASS' if validate_ok else 'FAIL (see output above)'}")
    print(f"  Reports written to: {report_dir.relative_to(ROOT)}/")
    print("\n  Next: review reports, test locally (cd website && npm run dev),")
    print("        then manually upload changed website/src/data/<state>/ files.")

    return 0 if (overall["all_pass"] and validate_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
