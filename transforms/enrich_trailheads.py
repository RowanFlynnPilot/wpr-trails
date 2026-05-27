"""Snap a trailhead coordinate onto each trail using nearby OSM parking.

For every trail in data/processed/trails/, queries Overpass for any
amenity=parking within TRAILHEAD_SEARCH_RADIUS_M of the trail line. Picks the
parking closest to any trail endpoint and writes the matching endpoint into
the trail's derived.trailhead_coords (lng, lat).

Trail JSONs that already have a non-null trailhead_coords are skipped, so the
script is resume-safe and idempotent. To force a refresh, set the field back
to null in the trail JSON before running.

Also writes derived.parking_distance_m so reviewers can see how far the
nearest lot actually is.
"""

import json
import math
import time
from pathlib import Path

import requests

from transforms.build_index import write_index

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "wpr-trails/0.1 (https://github.com/RowanFlynnPilot/wpr-trails)"

TRAILS_DIR = Path("data/processed/trails")
INDEX_PATH = Path("data/processed/index.json")

TRAILHEAD_SEARCH_RADIUS_M = 500   # parking must be within this distance of trail line
MAX_TRAILHEAD_DISTANCE_M = 1500   # if nearest parking is farther from any trail endpoint
                                  # than this, we don't really have a trailhead — long
                                  # linear trails like Wiouwash have parking miles away
                                  # from any endpoint but countless road-crossing access
                                  # points in between
SAMPLE_COUNT = 10                 # points along trail used for "around:" query
RATE_LIMIT_SEC = 5.0              # Overpass fair-use
BACKOFF_SEC = 60.0
MAX_RETRIES = 3


def _haversine_m(a: tuple, b: tuple) -> float:
    """Distance in meters between two (lng, lat) points."""
    lng1, lat1 = a
    lng2, lat2 = b
    r = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    h = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def trail_endpoints(geom: dict) -> list:
    """Return the (lng, lat) tuples at the start and end of every linestring."""
    if geom["type"] == "LineString":
        coords = geom["coordinates"]
        return [tuple(coords[0]), tuple(coords[-1])]
    if geom["type"] == "MultiLineString":
        out = []
        for line in geom["coordinates"]:
            out.append(tuple(line[0]))
            out.append(tuple(line[-1]))
        return out
    raise ValueError(f"Unexpected geometry type: {geom['type']}")


def _sample_along(coords: list, n: int = SAMPLE_COUNT) -> list:
    if len(coords) <= n:
        return list(coords)
    step = len(coords) / n
    return [coords[int(i * step)] for i in range(n)]


def trail_sample_points(geom: dict) -> list:
    if geom["type"] == "LineString":
        return _sample_along(geom["coordinates"])
    if geom["type"] == "MultiLineString":
        flat = [c for line in geom["coordinates"] for c in line]
        return _sample_along(flat)
    raise ValueError(f"Unexpected geometry type: {geom['type']}")


def fetch_parking_near(trail: dict) -> list:
    """Return [(lng, lat), ...] for amenity=parking features near the trail.

    Ways use their tag-provided center; nodes use their own coords.
    """
    points = trail_sample_points(trail["geometry"])
    around = ",".join(f"{lat},{lng}" for lng, lat in points)
    near = f"around:{TRAILHEAD_SEARCH_RADIUS_M},{around}"
    q = f"""[out:json][timeout:90];
    (
      node["amenity"="parking"]({near});
      way["amenity"="parking"]({near});
    );
    out center tags;"""

    for attempt in range(MAX_RETRIES):
        res = requests.post(
            OVERPASS_URL,
            data={"data": q},
            headers={"User-Agent": USER_AGENT},
            timeout=180,
        )
        if res.status_code in (429, 504):
            print(f"    ({res.status_code} - waiting {BACKOFF_SEC:.0f}s before retry)")
            time.sleep(BACKOFF_SEC)
            continue
        res.raise_for_status()
        elements = res.json().get("elements", [])
        parking = []
        for el in elements:
            if el["type"] == "node":
                parking.append((el["lon"], el["lat"]))
            elif el["type"] == "way" and "center" in el:
                parking.append((el["center"]["lon"], el["center"]["lat"]))
        return parking
    raise RuntimeError(
        f"Overpass kept returning transient errors after {MAX_RETRIES} attempts"
    )


def pick_trailhead(endpoints: list, parking: list) -> tuple:
    """Return (trailhead_coord, distance_m_to_parking) or (None, None) if no parking.

    Picks the (endpoint, parking) pair with minimum haversine distance.
    """
    if not parking:
        return None, None
    best_dist = float("inf")
    best_endpoint = None
    for ep in endpoints:
        for pk in parking:
            d = _haversine_m(ep, pk)
            if d < best_dist:
                best_dist = d
                best_endpoint = ep
    return list(best_endpoint), round(best_dist)


def main() -> None:
    trail_files = sorted(TRAILS_DIR.glob("*.json"))
    if not trail_files:
        raise FileNotFoundError(f"No trails in {TRAILS_DIR} - run build_trails first")

    print(f"Snapping trailheads for {len(trail_files)} trails")
    started = time.time()
    set_count = 0
    skipped_existing = 0
    no_parking = 0

    for i, tp in enumerate(trail_files, 1):
        trail = json.loads(tp.read_text())
        if trail["derived"].get("trailhead_coords") is not None:
            skipped_existing += 1
            continue

        parking = fetch_parking_near(trail)
        endpoints = trail_endpoints(trail["geometry"])
        coords, dist_m = pick_trailhead(endpoints, parking)
        if coords is None:
            no_parking += 1
            print(
                f"  [{i:3d}/{len(trail_files)}] {trail['name'][:50]:50s}  "
                f"(no parking within {TRAILHEAD_SEARCH_RADIUS_M}m)"
            )
        elif dist_m > MAX_TRAILHEAD_DISTANCE_M:
            no_parking += 1
            print(
                f"  [{i:3d}/{len(trail_files)}] {trail['name'][:50]:50s}  "
                f"(nearest parking {dist_m}m away — skipping, exceeds {MAX_TRAILHEAD_DISTANCE_M}m)"
            )
        else:
            trail["derived"]["trailhead_coords"] = coords
            trail["derived"]["parking_distance_m"] = dist_m
            tp.write_text(json.dumps(trail, indent=2))
            set_count += 1
            print(
                f"  [{i:3d}/{len(trail_files)}] {trail['name'][:50]:50s}  "
                f"trailhead set, {dist_m}m to parking"
            )
        time.sleep(RATE_LIMIT_SEC)

    print("\nRebuilding index.json with trailhead_coords...")
    write_index(TRAILS_DIR, INDEX_PATH)

    elapsed = time.time() - started
    print(
        f"\nDone in {elapsed:.0f}s: "
        f"{set_count} set, {skipped_existing} already had one, "
        f"{no_parking} had no parking within {TRAILHEAD_SEARCH_RADIUS_M}m"
    )


if __name__ == "__main__":
    main()
