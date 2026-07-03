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


def entity_photo(qids, lat, lon, ctx):
    """First QID whose P625 is near (lat,lon) and has P18 -> filename."""
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
            return claims["P18"][0]["mainsnak"]["datavalue"]["value"]
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
            hero = m.get("mountain_hero") or ""
            if hero and not any(g in hero for g in GENERIC):
                continue
            if not (m.get("lat") and m.get("lon")):
                continue
            fn = entity_photo(search_qids(m["name"], ctx), m["lat"], m["lon"], ctx)
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
            time.sleep(0.4)
    print(f"✅ heroes replaced: {replaced}")


if __name__ == "__main__":
    main()
