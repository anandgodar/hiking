#!/usr/bin/env python3
"""
Batch-build every state with the fully automated pipeline.

Runs scripts/auto-state.py for each state in pipeline.config.json using its
per-state import tuning. Queued execution (default 1 worker, max 3) with pauses
between states — Overpass and the government ArcGIS services rate-limit, so
this is deliberately not 50-way parallel.

Resumable: progress is tracked in pipeline-reports/auto-all-progress.json.
States already completed (or that already have a data folder) are skipped
unless --force. Failures don't stop the batch; they're listed at the end and
retried on the next run.

Usage:
  python3 scripts/auto-all.py                       # every state, one at a time
  python3 scripts/auto-all.py --workers 2           # gentle parallelism
  python3 scripts/auto-all.py --states colorado utah wyoming
  python3 scripts/auto-all.py --limit 5             # first 5 pending states
  python3 scripts/auto-all.py --force --states virginia   # redo a state
"""

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
DATA = ROOT / "website" / "src" / "data"
PROGRESS = ROOT / "pipeline-reports" / "auto-all-progress.json"
PAUSE_BETWEEN = 20  # seconds between state starts, per worker


def load_progress():
    if PROGRESS.exists():
        return json.loads(PROGRESS.read_text())
    return {"done": {}, "failed": {}}


def save_progress(prog):
    PROGRESS.parent.mkdir(exist_ok=True)
    PROGRESS.write_text(json.dumps(prog, indent=2) + "\n")


def build_state(slug):
    """Run auto-state for one slug; returns (slug, ok, seconds)."""
    t0 = time.time()
    log_dir = ROOT / "pipeline-reports" / "auto-all-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log = log_dir / f"{slug}.log"
    with open(log, "w") as fh:
        r = subprocess.run(
            [sys.executable, str(SCRIPTS / "auto-state.py"), slug],
            stdout=fh, stderr=subprocess.STDOUT,
        )
    return slug, r.returncode == 0, round(time.time() - t0)


def live_draft(slug):
    live = draft = 0
    d = DATA / slug
    if not d.is_dir():
        return 0, 0
    for f in d.glob("*.json"):
        try:
            rec = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue
        t = (rec.get("trails") or [{}])[0]
        ok = (not rec.get("_status") and (t.get("geo") or {}).get("path")
              and ((t.get("stats") or {}).get("distance") or 0) > 0)
        if ok:
            live += 1
        else:
            draft += 1
    return live, draft


def main():
    p = argparse.ArgumentParser(description="Batch state builder")
    p.add_argument("--states", nargs="*", help="only these slugs")
    p.add_argument("--limit", type=int, help="max states this run")
    p.add_argument("--workers", type=int, default=1, choices=[1, 2, 3])
    p.add_argument("--force", action="store_true",
                   help="re-run even if already done / has data")
    args = p.parse_args()

    cfg = json.loads((ROOT / "pipeline.config.json").read_text())
    all_slugs = [s["slug"] for s in cfg.get("states", [])]
    wanted = args.states or all_slugs
    unknown = [s for s in wanted if s not in all_slugs]
    if unknown:
        sys.exit(f"❌ Unknown state slug(s): {', '.join(unknown)}")

    prog = load_progress()
    pending = []
    for slug in wanted:
        if not args.force:
            if slug in prog["done"]:
                continue
            if (DATA / slug).is_dir() and any((DATA / slug).glob("*.json")):
                # Has data from before this runner; count it done, don't redo.
                prog["done"][slug] = {"note": "pre-existing data",
                                      "at": datetime.now().isoformat(timespec="seconds")}
                continue
        pending.append(slug)
    save_progress(prog)

    if args.limit:
        pending = pending[: args.limit]
    if not pending:
        print("Nothing to do — all requested states are done. "
              "Use --force to rebuild.")
        return

    print(f"Batch: {len(pending)} state(s), {args.workers} worker(s), "
          f"{PAUSE_BETWEEN}s stagger\n  queue: {', '.join(pending)}")

    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {}
        for i, slug in enumerate(pending):
            if i:
                time.sleep(PAUSE_BETWEEN)
            print(f"▶ starting {slug} "
                  f"(log: pipeline-reports/auto-all-logs/{slug}.log)")
            futures[ex.submit(build_state, slug)] = slug
        for fut in as_completed(futures):
            slug, ok, secs = fut.result()
            live, draft = live_draft(slug)
            results.append((slug, ok, secs, live, draft))
            prog = load_progress()
            if ok:
                prog["done"][slug] = {"live": live, "draft": draft, "secs": secs,
                                      "at": datetime.now().isoformat(timespec="seconds")}
                prog["failed"].pop(slug, None)
            else:
                prog["failed"][slug] = {"secs": secs,
                                        "at": datetime.now().isoformat(timespec="seconds")}
            save_progress(prog)
            print(f"  {'✅' if ok else '❌'} {slug}: {live} live / {draft} draft "
                  f"({secs}s)")

    print(f"\n{'=' * 62}\nBATCH SUMMARY\n{'=' * 62}")
    tot_live = tot_draft = 0
    for slug, ok, secs, live, draft in sorted(results):
        tot_live += live; tot_draft += draft
        print(f"  {slug:<16} {'ok' if ok else 'FAILED':<7} "
              f"{live:>4} live / {draft:>3} draft   {secs}s")
    print(f"\n  totals this run: {tot_live} live / {tot_draft} draft")
    failed = [r[0] for r in results if not r[1]]
    if failed:
        print(f"  retry failed states: python3 scripts/auto-all.py --states "
              f"{' '.join(failed)}")


if __name__ == "__main__":
    main()
