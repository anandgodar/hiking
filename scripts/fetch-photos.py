#!/usr/bin/env python3
"""
Fetch real peak photos from Wikimedia Commons via Wikidata.

Most imported peaks carry a Wikidata QID (from OSM). Wikidata's P18 property
points to that peak's photo on Wikimedia Commons — real photographs of the
actual mountain, under free licenses. This replaces the generic Unsplash
placeholder heroes with the real thing and records proper attribution
(artist, license, file page) in `hero_credit` for display.

Only trails whose hero is missing or a known generic placeholder are touched;
hand-picked photos are never overwritten. Batched API calls (50 QIDs per
request), polite pacing.

Usage:
  python3 scripts/fetch-photos.py                 # all states
  python3 scripts/fetch-photos.py --state colorado
"""

import glob
import html
import json
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "website" / "src" / "data"
UA = {"User-Agent": "summitseeker/1.0 (trail photo enrichment)"}

# The generic placeholders we want to replace (real photos are kept).
GENERIC = ("images.unsplash.com",)


def ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def api(url, ctx, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=40, context=ctx) as r:
                return json.loads(r.read())
        except Exception:
            time.sleep(2 * (attempt + 1))
    return {}


# A Wikidata item's P18 "image" claim is sometimes a photo of something near
# the peak rather than the peak itself (a post office, a park-entrance sign,
# an NRHP historic-district building tagged "H.D." in the standard
# nomination-photo naming pattern) — real cases hit in this codebase:
# Sentinel Butte, ND got a post-office photo; Mount Philo, VT got a
# park-entrance sign. Reject filenames that read as clearly non-scenic.
NON_SCENIC_FILENAME = re.compile(
    r"\b(post office|entrance|boundary marker|h\.?d\.?,|historic district|"
    r"plaque|sign\b|parking|restroom|visitor center|city hall|courthouse|"
    r"town hall|cemetery|church|school|museum)\b", re.I)


def batch_p18(qids, ctx):
    """QID -> Commons filename, 50 at a time via wbgetentities."""
    out = {}
    for i in range(0, len(qids), 50):
        chunk = qids[i:i + 50]
        u = ("https://www.wikidata.org/w/api.php?action=wbgetentities"
             f"&ids={'|'.join(chunk)}&props=claims&format=json")
        data = api(u, ctx)
        for qid, ent in (data.get("entities") or {}).items():
            claims = (ent.get("claims") or {}).get("P18") or []
            if claims:
                try:
                    fn = claims[0]["mainsnak"]["datavalue"]["value"]
                    if not NON_SCENIC_FILENAME.search(fn):
                        out[qid] = fn
                except (KeyError, IndexError):
                    pass
        time.sleep(0.3)
    return out


def batch_meta(filenames, ctx):
    """Commons filename -> {license, artist}, 50 titles at a time."""
    out = {}
    names = list(filenames)
    for i in range(0, len(names), 50):
        chunk = names[i:i + 50]
        titles = "|".join("File:" + n for n in chunk)
        u = ("https://commons.wikimedia.org/w/api.php?action=query"
             f"&titles={urllib.parse.quote(titles)}"
             "&prop=imageinfo&iiprop=extmetadata&format=json")
        data = api(u, ctx)
        for page in (data.get("query", {}).get("pages") or {}).values():
            title = (page.get("title") or "").removeprefix("File:")
            info = (page.get("imageinfo") or [{}])[0].get("extmetadata") or {}
            artist_html = info.get("Artist", {}).get("value", "")
            artist = html.unescape(re.sub(r"<[^>]+>", "", artist_html)).strip()
            out[title] = {
                "license": info.get("LicenseShortName", {}).get("value", ""),
                "artist": artist[:120],
            }
        time.sleep(0.3)
    return out


def hero_url(filename, width=1600):
    return ("https://commons.wikimedia.org/wiki/Special:FilePath/"
            + urllib.parse.quote(filename) + f"?width={width}")


def main():
    args = sys.argv[1:]
    pattern = "website/src/data/*/*.json"
    if "--state" in args:
        i = args.index("--state")
        pattern = f"website/src/data/{args[i + 1]}/*.json"

    ctx = ssl_context()
    # collect candidates: live, wikidata QID, generic/missing hero
    cands = []
    for f in glob.glob(str(ROOT / pattern)):
        if "/blog/" in f or "/guides/" in f or "_rejected" in f:
            continue
        d = json.loads(Path(f).read_text())
        if d.get("_status"):
            continue
        qid = (d.get("osm") or {}).get("wikidata")
        hero = d.get("mountain_hero") or ""
        if qid and (not hero or any(g in hero for g in GENERIC)):
            cands.append((f, qid))
    print(f"candidates (live, wikidata, generic/missing hero): {len(cands)}")
    if not cands:
        return

    p18 = batch_p18(sorted({q for _, q in cands}), ctx)
    print(f"peaks with a Commons photo: {len(p18)}")
    meta = batch_meta(sorted(set(p18.values())), ctx)

    updated = 0
    for f, qid in cands:
        filename = p18.get(qid)
        if not filename:
            continue
        m = meta.get(filename, {})
        d = json.loads(Path(f).read_text())
        d["mountain_hero"] = hero_url(filename)
        d["hero_credit"] = {
            "source": "Wikimedia Commons",
            "file": f"https://commons.wikimedia.org/wiki/File:{urllib.parse.quote(filename)}",
            "license": m.get("license", ""),
            "artist": m.get("artist", ""),
        }
        Path(f).write_text(json.dumps(d, indent=2) + "\n")
        updated += 1
    print(f"✅ heroes replaced with real peak photos: {updated}")


if __name__ == "__main__":
    main()
