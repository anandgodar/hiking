#!/usr/bin/env python3
"""
Compare each trail's elevation against USGS — REPORT ONLY, never overwrites.

The validator warns when an elevation is a round multiple of 100 ft, but many
official summit elevations genuinely ARE round numbers (Mount Carrigain really
is 4,700 ft). So a round number is not automatically wrong, and blindly
replacing it with a USGS point sample — which reads the digital elevation model
at the stored coordinate, often slightly off the true summit — can make accurate
data worse.

This tool therefore only *reports*: it queries the USGS Elevation Point Query
Service (EPQS) at each summit coordinate and flags trails where the stored value
diverges from the USGS sample by more than --threshold feet (default 75). Those
are the ones worth verifying by hand against a USGS benchmark or PeakBagger —
you decide and edit, the script does not.

Usage:
  python3 scripts/check-elevation.py --state new-hampshire
  python3 scripts/check-elevation.py --state california --threshold 100
  python3 scripts/check-elevation.py --rounded-only --state maine
"""

import glob
import json
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "website" / "src" / "data"
EPQS = "https://epqs.nationalmap.gov/v1/json"


def ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def usgs_elevation(lat, lon, ctx, retries=3):
    qs = urllib.parse.urlencode({"x": lon, "y": lat, "units": "Feet",
                                 "wkid": 4326, "includeDate": "false"})
    req = urllib.request.Request(f"{EPQS}?{qs}",
                                 headers={"User-Agent": "summitseeker-elev/1.0"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=40, context=ctx) as resp:
                val = json.loads(resp.read()).get("value")
            if val is None or float(val) < -1000:
                return None
            return round(float(val))
        except urllib.error.URLError as e:
            if "CERTIFICATE_VERIFY_FAILED" in str(e):
                sys.exit("❌ TLS cert verification failed (macOS/python.org). Fix:\n"
                         "   /Applications/Python\\ 3.13/Install\\ Certificates.command\n"
                         "   or: pip3 install --upgrade certifi")
            time.sleep(2 ** attempt)
        except Exception:
            time.sleep(2 ** attempt)
    return None


def main():
    args = sys.argv[1:]
    threshold = 75
    if "--threshold" in args:
        i = args.index("--threshold")
        threshold = float(args[i + 1]); args = args[:i] + args[i + 2:]
    rounded_only = "--rounded-only" in args
    args = [a for a in args if a != "--rounded-only"]
    files = []
    if "--state" in args:
        i = args.index("--state")
        files = sorted(glob.glob(str(DATA / args[i + 1] / "*.json")))
        args = args[:i] + args[i + 2:]
    files += [a for a in args if a.endswith(".json")]
    if not files:
        print("Usage: python3 scripts/check-elevation.py [--threshold FT] "
              "[--rounded-only] (--state <slug> | <file.json> ...)")
        sys.exit(1)

    ctx = ssl_context()
    flagged = checked = 0
    print(f"{'TRAIL':<30} {'STORED':>8} {'USGS':>8} {'DIFF':>7}")
    print("-" * 56)
    for f in files:
        d = json.loads(Path(f).read_text())
        elev, lat, lon = d.get("elevation"), d.get("lat"), d.get("lon")
        if elev is None or lat is None or lon is None:
            continue
        if rounded_only and not (elev % 100 == 0 and elev > 1000):
            continue
        usgs = usgs_elevation(lat, lon, ctx)
        checked += 1
        time.sleep(0.3)
        if usgs is None:
            continue
        diff = elev - usgs
        if abs(diff) > threshold:
            flagged += 1
            print(f"{d.get('name','?'):<30} {elev:>8} {usgs:>8} {diff:>+7}  "
                  f"⚠️  verify")

    print("-" * 56)
    print(f"Checked {checked} trail(s); {flagged} diverge from USGS by "
          f">{threshold} ft and are worth a manual benchmark check.")
    print("Note: USGS here is a point sample at the stored coordinate, not a "
          "summit benchmark — a large diff often means the coordinate is off "
          "the true summit, not that the elevation is wrong. Verify before editing.")


if __name__ == "__main__":
    main()
