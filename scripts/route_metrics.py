#!/usr/bin/env python3
"""
Canonical route measurements: length, shape, and the HIKED distance.

Single source of truth for what `distance` means, shared by the ingest
pipeline (fetch-trails.py, fetch-named-route.py), the migration, the publish
gate and the build validator — so the semantics cannot drift between them.

The bug this exists to prevent: route geometry gives the trailhead->summit
length, which was stored directly as `distance` and fed to the NPS difficulty
formula. That formula expects the distance actually hiked. For an out-and-back
summit route the hiked distance is twice the geometry, so difficulty was
understated by sqrt(2) (~29%) on ~706 published trails.

Fields produced:
  route_length_mi  computed length of the stored geometry (always one traverse)
  distance_type    "loop" | "out-and-back"
  distance         the HIKED distance the difficulty formula must receive

A route is a loop when its endpoints meet; otherwise it is out-and-back, and
the hiker must return the way they came. `distance_type` is written to the
record so the page can state the basis explicitly ("out-and-back — 8.6 mi
round trip") rather than publishing an unlabeled number.
"""

import math

# Endpoints closer than this fraction of total length are treated as the same
# place, i.e. the route closes on itself.
LOOP_CLOSURE_FRACTION = 0.15


def haversine_mi(a, b):
    R = 3959.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dlat = math.radians(b[0] - a[0])
    dlon = math.radians(b[1] - a[1])
    h = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(h))


def route_length_mi(path):
    """Length of one traverse of the stored geometry, in miles."""
    if not path or len(path) < 2:
        return 0.0
    return sum(haversine_mi(path[i - 1], path[i]) for i in range(1, len(path)))


def is_loop(path):
    """True when the route returns to its own start."""
    if not path or len(path) < 2:
        return False
    total = route_length_mi(path)
    if total <= 0:
        return False
    return haversine_mi(path[0], path[-1]) < LOOP_CLOSURE_FRACTION * total


def hiked_distance_mi(path):
    """Distance actually covered: loops once, out-and-backs twice.

    Returns (distance, route_length, distance_type).
    """
    length = route_length_mi(path)
    if is_loop(path):
        return round(length, 1), round(length, 2), "loop"
    return round(length * 2, 1), round(length, 2), "out-and-back"


def apply_to_trail(trail):
    """Write route_length_mi / distance_type / distance onto a trail dict.

    Returns True when the record changed. An AUTHORED distance (one that
    disagrees with the geometry by more than the tolerance below, e.g. a
    curated round-trip figure sitting on partial geometry) is preserved and
    marked, never overwritten with a geometry-derived number — the authored
    value is the correct one; the geometry is what is incomplete.
    """
    geo = trail.get("geo") or {}
    path = geo.get("path") or []
    if len(path) < 2:
        return False
    stats = trail.setdefault("stats", {})
    distance, length, dtype = hiked_distance_mi(path)
    before = (stats.get("distance"), stats.get("route_length_mi"),
              stats.get("distance_type"), stats.get("distance_source"))

    stats["route_length_mi"] = length
    stats["distance_type"] = dtype

    stored = stats.get("distance")
    authored = (
        stats.get("distance_source") == "authored"
        or (stored and length > 0 and abs(stored - length) / max(stored, 0.01) > 0.10
            and abs(stored - distance) / max(stored, 0.01) > 0.10)
    )
    if authored:
        # Curated value on incomplete geometry — keep it, flag it for review.
        stats["distance_source"] = "authored"
    else:
        stats["distance"] = distance
        stats["distance_source"] = "computed"

    return before != (stats.get("distance"), stats.get("route_length_mi"),
                      stats.get("distance_type"), stats.get("distance_source"))
