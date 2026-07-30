#!/usr/bin/env python3
"""
Fetch Commons peak photos by NAME for trails without an OSM Wikidata QID.

fetch-photos.py needs `osm.wikidata`; hand-curated trails (NH, ME, VT, NY,
CA originals) don't have it. This searches Wikidata by peak name, verifies
the hit is the same mountain by coordinate proximity (P625 within ~15 km),
then pulls P18 exactly like fetch-photos.py. Coordinate check means a
same-named peak in another state can never be attached.

Usage:
  python3 scripts/fetch-photos-by-name.py --state new-hampshire [...]
"""

import glob
import json
import math
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
GENERIC = ("images.unsplash.com",)
MAX_KM = 15.0

# These specific peaks have failed automated matching multiple times across
# independent runs (their Wikidata item's linked photo is reliably wrong —
# an ironworks furnace and a boundary marker for Mount Riga, a wind farm in a
# different state for Bakke Mountain). Keyword filtering catches new
# variants of the general defect class but these two keep finding fresh bad
# candidates, so stop trying rather than keep whack-a-moling by hand.
NEVER_AUTO_MATCH = {"mount-riga-ct", "bakke-mountain-ma"}


def ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def api(url, ctx, retries=5):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=40, context=ctx) as r:
                body = r.read()
            return json.loads(body)
        except json.JSONDecodeError:
            # Wikimedia's rate-limit response is HTTP 200 with a plain-text
            # body ("You are making too many requests..."), not an HTTP
            # error — a short retry loop just fires again immediately and
            # burns the whole budget in seconds. Back off hard.
            print(f"    · rate-limited, backing off {15 * (attempt + 1)}s "
                  f"[{attempt + 1}/{retries}]")
            time.sleep(15 * (attempt + 1))
        except Exception:
            time.sleep(2 * (attempt + 1))
    return {}


def km(a_lat, a_lon, b_lat, b_lon):
    r = 6371
    dlat = math.radians(b_lat - a_lat)
    dlon = math.radians(b_lon - a_lon)
    h = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(a_lat)) * math.cos(math.radians(b_lat)) *
         math.sin(dlon / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(h))


def search_qids(name, ctx):
    q = urllib.parse.quote(name)
    url = (f"https://www.wikidata.org/w/api.php?action=wbsearchentities"
           f"&search={q}&language=en&type=item&limit=5&format=json")
    return [h["id"] for h in api(url, ctx).get("search", [])]


# A Wikidata item's P18 "image" claim is sometimes a photo of something near
# the peak rather than the peak itself — a coordinate check alone can't catch
# this, since the off-subject photo is still genuinely close by (a boundary
# marker, a post office, a park entrance sign, a historic-district building
# tagged "H.D." in the standard NRHP nomination-photo naming pattern). Two
# real trails this exact filter was written for: Sentinel Butte, ND got a
# post-office photo, and Mount Philo, VT got a park-entrance sign — both
# published, then removed, then re-matched by an independent run before this
# filter existed. Reject filenames that are clearly not a landscape photo of
# the peak rather than trying to guess what a good one looks like.
NON_SCENIC_FILENAME = re.compile(
    r"\b(post office|entrance|boundary marker|h\.?d\.?,|historic district|"
    r"plaque|\bsign\b|parking|restroom|visitor center|city hall|courthouse|"
    r"town hall|cemetery|church|school|museum|furnace|ironworks|foundry|"
    r"quarry|\bmill\b|factory)", re.I)
# Note: no trailing \b on the group as a whole -- several alternatives end
# in punctuation ("h.d.,"), and \b only fires at a word/non-word transition,
# so a trailing comma followed by a space never satisfies it. This missed
# "MOUNT ARLINGTON H.D., ..." (an NRHP building photo) on a live run before
# the bug was caught. Individual alternatives that are common English words
# keep their own \b to avoid matching inside longer words (sign vs
# assignment, mill vs million).


def entity_photo(qids, lat, lon, ctx):
    """First QID whose P625 is near (lat,lon), has P18, and looks scenic."""
    if not qids:
        return None
    url = ("https://www.wikidata.org/w/api.php?action=wbgetentities"
           f"&ids={'|'.join(qids)}&props=claims&format=json")
    ents = api(url, ctx).get("entities", {})
    for qid in qids:
        claims = ents.get(qid, {}).get("claims", {})
        try:
            c = claims["P625"][0]["mainsnak"]["datavalue"]["value"]
            if km(lat, lon, c["latitude"], c["longitude"]) > MAX_KM:
                continue
            fn = claims["P18"][0]["mainsnak"]["datavalue"]["value"]
            if NON_SCENIC_FILENAME.search(fn):
                continue
            return fn
        except (KeyError, IndexError, TypeError):
            continue
    return None


def commons_meta(filename, ctx):
    t = urllib.parse.quote("File:" + filename)
    url = ("https://commons.wikimedia.org/w/api.php?action=query"
           f"&titles={t}&prop=imageinfo&iiprop=extmetadata&format=json")
    pages = api(url, ctx).get("query", {}).get("pages", {})
    for p in pages.values():
        md = (p.get("imageinfo") or [{}])[0].get("extmetadata", {})
        lic = md.get("LicenseShortName", {}).get("value", "")
        artist = md.get("Artist", {}).get("value", "")
        import re
        artist = re.sub(r"<[^>]+>", "", artist).strip()
        return lic, artist
    return "", ""


def main():
    states = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--state" in sys.argv:
        states = sys.argv[sys.argv.index("--state") + 1:]
    ctx = ssl_context()
    replaced = 0
    for state in states:
        for path in sorted(glob.glob(str(DATA / state / "*.json"))):
            try:
                m = json.loads(Path(path).read_text())
            except Exception:
                continue
            if not isinstance(m, dict) or m.get("_status") or not m.get("name"):
                continue
            if m.get("slug") in NEVER_AUTO_MATCH:
                continue
            hero = m.get("mountain_hero") or ""
            if hero and not any(g in hero for g in GENERIC):
                continue
            if not (m.get("lat") and m.get("lon")):
                continue
            fn = entity_photo(search_qids(m["name"], ctx), m["lat"], m["lon"], ctx)
            # Pace every lookup, not just successful ones — most peaks have
            # no match, and firing those requests back-to-back with no
            # delay is what triggers Wikimedia's rate limit in the first
            # place (it did, mid-run, on the first attempt at this).
            time.sleep(0.5)
            if not fn:
                continue
            lic, artist = commons_meta(fn, ctx)
            enc = urllib.parse.quote(fn.replace(" ", "_"))
            m["mountain_hero"] = (
                f"https://commons.wikimedia.org/wiki/Special:FilePath/{enc}?width=1600")
            m["hero_credit"] = {
                "source": "Wikimedia Commons",
                "file": f"https://commons.wikimedia.org/wiki/File:{enc}",
                "license": lic or "See file page",
                "artist": artist,
            }
            Path(path).write_text(json.dumps(m, indent=2) + "\n")
            replaced += 1
            print(f"  ✓ {state}/{m['slug']}: {fn}")
    print(f"✅ heroes replaced: {replaced}")


if __name__ == "__main__":
    main()
