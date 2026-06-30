#!/usr/bin/env python3
"""
Fill missing elevation on a trail's GPS path from the Open-Meteo DEM.

A GPS path is sometimes 2-D — a recorded track with no elevation, or geometry
that came without it — which leaves the elevation chart flat and the gain wrong.
This batch-queries the free Open-Meteo elevation API (Copernicus 30 m DEM, no
key) for each path point and writes real elevations, then recomputes the trail's
elevation chart and gain.

It only touches paths whose elevation is missing or essentially flat — paths
that already carry real elevation (e.g. from a 3-D GPX) are left alone. It does
NOT invent or fetch the *route* itself (open data has no reliable per-peak
route); supply that via a real GPX.

Usage:
  python3 scripts/enrich-elevation.py --state virginia
  python3 scripts/enrich-elevation.py website/src/data/virginia/mount-rogers-va.json
"""

import glob
import json
import math
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "website" / "src" / "data"
ELEV_API = "https://api.open-meteo.com/v1/elevation"


def ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def haversine_mi(a, b):
    R = 3959
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dlat = math.radians(b[0] - a[0])
    dlon = math.radians(b[1] - a[1])
    h = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(h))


def batch_elevations(points, ctx):
    """Open-Meteo allows many coords per call; chunk to be safe."""
    out = []
    for i in range(0, len(points), 100):
        chunk = points[i:i + 100]
        lats = ",".join(f"{p[0]:.6f}" for p in chunk)
        lons = ",".join(f"{p[1]:.6f}" for p in chunk)
        url = f"{ELEV_API}?{urllib.parse.urlencode({'latitude': lats, 'longitude': lons})}"
        req = urllib.request.Request(url, headers={"User-Agent": "summitseeker-elev/1.0"})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=40, context=ctx) as resp:
                    data = json.loads(resp.read())
                out.extend(data.get("elevation") or [])
                break
            except urllib.error.URLError as e:
                if "CERTIFICATE_VERIFY_FAILED" in str(e):
                    sys.exit("❌ TLS cert verification failed (macOS/python.org). Fix:\n"
                             "   /Applications/Python\\ 3.13/Install\\ Certificates.command\n"
                             "   or: pip3 install --upgrade certifi")
                time.sleep(2 ** attempt)
            except Exception:
                time.sleep(2 ** attempt)
        time.sleep(0.2)
    return out


def needs_elevation(path):
    """True if the path has no real elevation (2-D points or all ~0/flat)."""
    eles = [p[2] for p in path if len(p) >= 3 and isinstance(p[2], (int, float))]
    if len(eles) < len(path):
        return True               # some points are 2-D
    if not eles:
        return True
    return max(eles) - min(eles) < 5  # essentially flat → not real elevation


def build_chart(path, num=15):
    dists = [0.0]
    for i in range(1, len(path)):
        dists.append(dists[-1] + haversine_mi(path[i - 1], path[i]))
    total = dists[-1]
    chart = []
    if total <= 0:
        return chart
    step = total / (num - 1)
    for i in range(num):
        target = i * step
        idx = min(range(len(dists)), key=lambda j: abs(dists[j] - target))
        chart.append({"distance": round(target, 2), "elevation": round(path[idx][2])})
    return chart


def process(path_file, ctx):
    d = json.loads(Path(path_file).read_text())
    t = (d.get("trails") or [{}])[0]
    geo = t.get("geo") or {}
    path = geo.get("path") or []
    if not path:
        return False
    if not needs_elevation(path):
        return False

    pts = [(p[0], p[1]) for p in path]
    eles = batch_elevations(pts, ctx)
    if len(eles) != len(pts):
        print(f"  · elevation fetch incomplete, skipped: {d.get('name')}")
        return False

    new_path = [[p[0], p[1], round(e)] for p, e in zip(path, eles)]
    geo["path"] = new_path
    geo["chart"] = build_chart(new_path)
    t["geo"] = geo
    stats = t.setdefault("stats", {})
    stats["gain"] = round(max(eles) - min(eles))
    ds = d.setdefault("data_sources", {})
    ds["elevation_source"] = "Open-Meteo (Copernicus 30 m DEM)"
    ds["elevation_verified"] = str(date.today())
    Path(path_file).write_text(json.dumps(d, indent=2) + "\n")
    print(f"  ✅ {d.get('name'):<28} {len(new_path)} pts, gain {stats['gain']} ft")
    return True


def main():
    args = sys.argv[1:]
    files = []
    if "--state" in args:
        i = args.index("--state")
        files = sorted(glob.glob(str(DATA / args[i + 1] / "*.json")))
        args = args[:i] + args[i + 2:]
    files += [a for a in args if a.endswith(".json")]
    if not files:
        print("Usage: python3 scripts/enrich-elevation.py "
              "(--state <slug> | <file.json> ...)")
        sys.exit(1)
    ctx = ssl_context()
    n = sum(bool(process(f, ctx)) for f in files)
    print(f"\nFilled elevation on {n} trail(s) from Open-Meteo.")


if __name__ == "__main__":
    main()
