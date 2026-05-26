"""Sample elevations along each trail's geometry and populate elevation fields.

Uses USGS 3DEP 10m DEM (NED10m dataset) via Open Topo Data's batch endpoint.
Single canonical US elevation source, no auth needed, free public tier.

Sampling: every ~100m along trail geometry. For a 5mi trail that's ~80 points;
for the longest trails (76mi state trails) ~1200 points. Resolution is sufficient
for elevation gain calculation in central Wisconsin's rolling terrain.

Idempotent. Always re-enriches all trails - 2-3 min weekly cost is acceptable.
"""

import json
import math
import time
from pathlib import Path
from typing import Iterator

import requests

from transforms.build_index import write_index

TRAILS_DIR = Path("data/processed/trails")
INDEX_PATH = Path("data/processed/index.json")

ENDPOINT = "https://api.opentopodata.org/v1/ned10m"
USER_AGENT = "wpr-trails/0.1 (https://github.com/RowanFlynnPilot/wpr-trails)"
SAMPLE_INTERVAL_M = 100
BATCH_SIZE = 100              # Open Topo Data public limit
RATE_LIMIT_SEC = 1.0          # Open Topo Data public rate cap


# --- Geometry helpers -----------------------------------------------------

def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def sample_along_line(coords: list, interval_m: float) -> Iterator:
    """Yield (lng, lat) points at ~interval_m spacing along the line.

    Always emits the first and last vertex; intermediate samples land at
    cumulative-distance crossings of `interval_m`.
    """
    if len(coords) < 2:
        return
    yield tuple(coords[0])
    accumulated = 0.0
    next_threshold = interval_m
    for i in range(len(coords) - 1):
        x1, y1 = coords[i]
        x2, y2 = coords[i + 1]
        seg_len = haversine_m(y1, x1, y2, x2)
        if seg_len == 0:
            continue
        seg_start = accumulated
        accumulated += seg_len
        while next_threshold <= accumulated:
            t = (next_threshold - seg_start) / seg_len
            yield (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
            next_threshold += interval_m
    yield tuple(coords[-1])


def all_samples(geom: dict) -> list:
    """Sample points across either a LineString or MultiLineString."""
    if geom["type"] == "LineString":
        return list(sample_along_line(geom["coordinates"], SAMPLE_INTERVAL_M))
    if geom["type"] == "MultiLineString":
        points = []
        for line_coords in geom["coordinates"]:
            points.extend(sample_along_line(line_coords, SAMPLE_INTERVAL_M))
        return points
    raise ValueError(f"Unexpected geometry type: {geom['type']}")


# --- Elevation API --------------------------------------------------------

def fetch_elevations(points: list) -> list:
    """Query Open Topo Data in batches. Returns elevations in input order."""
    elevations = []
    for i in range(0, len(points), BATCH_SIZE):
        batch = points[i:i + BATCH_SIZE]
        loc_str = "|".join(f"{lat:.5f},{lng:.5f}" for lng, lat in batch)
        response = requests.get(
            ENDPOINT,
            params={"locations": loc_str},
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "OK":
            raise RuntimeError(f"Open Topo Data returned non-OK status: {data}")
        for result in data["results"]:
            elev = result.get("elevation")
            if elev is None:
                raise RuntimeError(f"Null elevation at {result['location']}")
            elevations.append(elev)
        time.sleep(RATE_LIMIT_SEC)
    return elevations


# --- Profile computation --------------------------------------------------

def compute_profile(points: list, elevations: list) -> tuple:
    """Return (profile, gain_m, max_m, min_m).

    profile: list of [distance_from_start_m, elevation_m] pairs.
    gain_m: cumulative ascent (sum of positive deltas).
    """
    if len(points) != len(elevations):
        raise ValueError("points and elevations length mismatch")

    profile = [[0.0, elevations[0]]]
    cumulative = 0.0
    for i in range(1, len(points)):
        (x1, y1), (x2, y2) = points[i - 1], points[i]
        cumulative += haversine_m(y1, x1, y2, x2)
        profile.append([cumulative, elevations[i]])

    gain = sum(
        max(0.0, elevations[i] - elevations[i - 1])
        for i in range(1, len(elevations))
    )
    return profile, gain, max(elevations), min(elevations)


def estimate_difficulty(length_m: float, gain_m: float) -> str:
    """Difficulty bucket derived from length + cumulative elevation gain.

    Score: sqrt(miles)*2 + gain_ft/500. The sqrt(miles) term gives
    diminishing returns on length so long flat rail-trails don't overrate;
    the linear gain term captures vertical effort cleanly. Thresholds
    calibrated against ~10 trails with known local difficulty consensus
    in central Wisconsin.

    Disagreement with editorial.difficulty is acceptable - editorial
    captures terrain nuance (rocky, technical, well-graded) that
    mechanical length+gain alone can't.
    """
    miles = length_m / 1609.34
    gain_ft = gain_m * 3.281
    score = math.sqrt(miles) * 2 + gain_ft / 500
    if score < 3.5:
        return "easy"
    if score < 7:
        return "moderate"
    if score < 13:
        return "difficult"
    return "strenuous"


# --- Main -----------------------------------------------------------------

def enrich_trail(trail: dict) -> int:
    """Populate elevation_* fields on a trail dict in place. Returns sample count."""
    samples = all_samples(trail["geometry"])
    if not samples:
        raise RuntimeError(f"No samples produced for {trail['id']}")
    elevations = fetch_elevations(samples)
    profile, gain, hi, lo = compute_profile(samples, elevations)
    trail["attributes"]["elevation_gain_m"] = round(gain, 1)
    trail["attributes"]["elevation_max_m"] = round(hi, 1)
    trail["attributes"]["elevation_min_m"] = round(lo, 1)
    trail["attributes"]["elevation_profile"] = [
        [round(d, 1), round(e, 1)] for d, e in profile
    ]
    trail["attributes"]["difficulty_estimated"] = estimate_difficulty(
        trail["attributes"]["length_m"], gain
    )
    return len(samples)


def main() -> None:
    trail_files = sorted(TRAILS_DIR.glob("*.json"))
    if not trail_files:
        raise FileNotFoundError(f"No trails in {TRAILS_DIR} - run build_trails first")

    print(f"Enriching {len(trail_files)} trails (sample interval: {SAMPLE_INTERVAL_M}m)")
    total_samples = 0
    started = time.time()
    for trail_path in trail_files:
        trail = json.loads(trail_path.read_text())
        n_samples = enrich_trail(trail)
        trail_path.write_text(json.dumps(trail, indent=2))
        total_samples += n_samples
        attrs = trail["attributes"]
        miles = attrs["length_m"] / 1609.34
        gain_ft = attrs["elevation_gain_m"] * 3.281
        print(f"  {trail['id']:55s} {miles:6.2f}mi  gain={gain_ft:5.0f}ft  pts={n_samples:5d}")

    write_index(TRAILS_DIR, INDEX_PATH)
    elapsed = time.time() - started
    print(f"\nDone in {elapsed:.0f}s. Total sample points: {total_samples}")


if __name__ == "__main__":
    main()
