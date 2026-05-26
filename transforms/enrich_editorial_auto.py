"""Auto-derive editorial fields from spatial sources.

Writes data/editorial_auto.yaml with best-effort values for every trail.
Human-curated data/editorial.yaml takes precedence at score time (see
transforms/build_scores.py).

Sources used:
- OSM nearby features along trail geometry (scenery, parking)
- Trail attributes (difficulty_estimated, length, activities)
- Managing authority (dog policy default)
- Elevation profile (exposure heuristic)

Each derived value includes provenance in a parallel _provenance dict so the
human reviewer can see exactly where it came from.
"""

import json
import time
from collections import Counter
from pathlib import Path

import requests
import yaml

from transforms.forest_coverage import ForestIndex

TRAILS_DIR = Path("data/processed/trails")
OUTPUT_PATH = Path("data/editorial_auto.yaml")

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "wpr-trails/0.1 (https://github.com/RowanFlynnPilot/wpr-trails)"

SEARCH_RADIUS_M = 100             # scenery features within this distance count
PARKING_RADIUS_M = 300            # parking can be slightly further from trail line
SAMPLE_COUNT = 10                 # evenly-spaced points along each trail
RATE_LIMIT_SEC = 5.0              # Overpass fair-use buffer between queries
BACKOFF_SEC = 60.0                # wait on transient errors before retrying
MAX_RETRIES = 3


# --- Geometry sampling ----------------------------------------------------

def sample_along(coords: list, n: int = SAMPLE_COUNT) -> list:
    """Evenly-spaced subsample of trail coordinates."""
    if len(coords) <= n:
        return list(coords)
    step = len(coords) / n
    return [coords[int(i * step)] for i in range(n)]


def trail_sample_points(trail: dict) -> list:
    geom = trail["geometry"]
    if geom["type"] == "LineString":
        coords = geom["coordinates"]
    elif geom["type"] == "MultiLineString":
        coords = [c for line in geom["coordinates"] for c in line]
    else:
        raise ValueError(f"Unexpected geometry type: {geom['type']}")
    return sample_along(coords)


# --- OSM query ------------------------------------------------------------

def fetch_nearby_features(trail: dict) -> list:
    """Single Overpass query for all feature types we care about along the trail.

    Retries up to MAX_RETRIES times on 429 (Overpass tracks slot-time per IP,
    not just request count, so long queries can saturate even with paced calls).
    """
    points = trail_sample_points(trail)
    around = ",".join(f"{lat},{lng}" for lng, lat in points)
    near = f"around:{SEARCH_RADIUS_M},{around}"
    parking_near = f"around:{PARKING_RADIUS_M},{around}"

    q = f"""[out:json][timeout:120];
    (
      node["amenity"="parking"]({parking_near});
      way["amenity"="parking"]({parking_near});
      node["natural"="peak"]({near});
      node["natural"="cliff"]({near});
      node["tourism"="viewpoint"]({near});
      way["natural"="water"]({near});
      way["natural"="wetland"]({near});
      way["natural"="grassland"]({near});
      way["natural"="bare_rock"]({near});
      way["natural"="cliff"]({near});
      way["waterway"~"river|stream"]({near});
      way["landuse"="meadow"]({near});
    );
    out tags center;"""

    for attempt in range(MAX_RETRIES):
        response = requests.post(
            OVERPASS_URL,
            data={"data": q},
            headers={"User-Agent": USER_AGENT},
            timeout=180,
        )
        if response.status_code in (429, 504):
            print(f"    ({response.status_code} - waiting {BACKOFF_SEC:.0f}s before retry)")
            time.sleep(BACKOFF_SEC)
            continue
        response.raise_for_status()
        return response.json().get("elements", [])
    raise RuntimeError(f"Overpass kept returning transient errors after {MAX_RETRIES} attempts")


# --- Per-field derivation -------------------------------------------------

def derive_scenery_tags(features: list) -> tuple:
    """Map OSM feature types to our scenery_tags vocabulary."""
    tags = set()
    counts: Counter = Counter()
    for feat in features:
        tg = feat.get("tags", {})
        natural = tg.get("natural")
        waterway = tg.get("waterway")
        tourism = tg.get("tourism")
        landuse = tg.get("landuse")

        if natural == "water" or waterway in ("river", "stream"):
            tags.add("water"); counts["water"] += 1
        elif natural == "wetland":
            tags.add("wetland"); counts["wetland"] += 1
        elif natural == "grassland" or landuse == "meadow":
            tags.add("prairie"); counts["prairie"] += 1
        elif natural in ("bare_rock", "cliff"):
            tags.add("rocky_outcrop"); counts["rocky_outcrop"] += 1
        elif tourism == "viewpoint" or natural == "peak":
            tags.add("overlook"); counts["overlook"] += 1
    return sorted(tags), counts


def derive_parking(features: list) -> tuple:
    """Distinguish a designated lot (way) from roadside (single node)."""
    parking = [f for f in features if f.get("tags", {}).get("amenity") == "parking"]
    if not parking:
        return "none", 0
    has_lot = any(f["type"] == "way" for f in parking)
    if has_lot:
        return "large", len(parking)
    if len(parking) >= 2:
        return "small", len(parking)
    return "roadside", len(parking)


def derive_dog_policy(trail: dict) -> str:
    """WI state/county lands default to leashed."""
    auth = (trail["attributes"].get("managing_authority") or "").lower()
    if "dnr" in auth or "iata" in auth or "county" in auth:
        return "leashed"
    return "unknown"


def derive_exposure(trail: dict, forest_coverage: float) -> tuple:
    """Conservative exposure heuristic.

    Auto-deriving exposure from spatial data is genuinely hard - tree canopy,
    summit prominence, ridge orientation, and nearby water all matter. So this
    function takes a deliberately simple two-tier approach and the human-edited
    editorial.yaml overrides per-trail when nuance is needed.

    - High OSM forest coverage (>=30%) -> sheltered (confident)
    - High elevation (>570m, ~Rib Mountain area) -> exposed (confident)
    - Else -> sheltered (default; most central WI is forested even if OSM
      doesn't tag the polygon)
    """
    e_max = trail["attributes"].get("elevation_max_m") or 0
    pct = forest_coverage * 100

    if forest_coverage >= 0.30:
        return "sheltered", f"{pct:.0f}% of sample points in OSM forest polygons"

    if e_max > 570:
        return "exposed", (
            f"max elev {e_max:.0f}m suggests prominent ridge "
            f"(forest coverage {pct:.0f}%)"
        )

    return "sheltered", (
        f"default for central WI; OSM forest data sparse ({pct:.0f}%)"
    )


def derive_family_friendly(trail: dict) -> bool:
    attrs = trail["attributes"]
    diff = attrs.get("difficulty_estimated")
    miles = attrs.get("length_m", 0) / 1609.34
    return diff == "easy" and miles < 3


def derive_seasonality(trail: dict, scenery_tags: list) -> list:
    tags = set()
    activities = set(trail.get("activities") or [])
    if "snowshoe" in activities:
        tags.add("winter_snowshoe")
    if "xc_ski" in activities:
        tags.add("winter_xc")
    if "water" in scenery_tags or "wetland" in scenery_tags:
        tags.add("wildflower")
    if "overlook" in scenery_tags or "rocky_outcrop" in scenery_tags:
        tags.add("fall_color")
    return sorted(tags)


def derive_bike_allowed(trail: dict) -> bool:
    """State Trail layer carries this explicitly via activity codes; everything else conservative."""
    if trail["id"].startswith("state-"):
        # State trails default to multi-use unless the DNR codes said otherwise.
        # We don't currently carry BIKE_OFFRD_CODE through to the trail record,
        # but in central WI all 5 state trails in the bbox allow bikes per DNR data.
        return True
    return False


# --- Main -----------------------------------------------------------------

def enrich_trail(trail: dict, forest_index: ForestIndex) -> dict:
    features = fetch_nearby_features(trail)
    forest_cov = forest_index.coverage(trail_sample_points(trail))

    scenery, scenery_counts = derive_scenery_tags(features)
    parking, n_parking = derive_parking(features)
    dog_policy = derive_dog_policy(trail)
    exposure, exposure_note = derive_exposure(trail, forest_cov)
    family_friendly = derive_family_friendly(trail)
    seasonality = derive_seasonality(trail, scenery)
    bike_allowed = derive_bike_allowed(trail)

    return {
        "family_friendly": family_friendly,
        "dog_policy": dog_policy,
        "bike_allowed": bike_allowed,
        "parking": parking,
        "accessibility": "unknown",
        "scenery_tags": scenery,
        "seasonality": seasonality,
        "mud_susceptibility": "moderate",
        "exposure": exposure,
        "drainage": "loamy",
        "notes": None,
        "last_field_check": None,
        "validated": False,
        "_provenance": {
            "scenery_tags": f"OSM: {dict(scenery_counts)} features within {SEARCH_RADIUS_M}m",
            "parking": f"OSM: {n_parking} amenity=parking within {PARKING_RADIUS_M}m",
            "dog_policy": f"default for managing_authority='{trail['attributes'].get('managing_authority')}'",
            "exposure": exposure_note,
            "family_friendly": (
                f"difficulty={trail['attributes'].get('difficulty_estimated')}, "
                f"length={trail['attributes']['length_m']/1609.34:.1f}mi"
            ),
            "seasonality": "derived from activities + scenery_tags",
            "bike_allowed": "state-trail default; others conservative=false",
            "mud_susceptibility": "default 'moderate' (soil data enrichment is Phase 2)",
            "drainage": "default 'loamy' (soil data enrichment is Phase 2)",
        },
    }


def main() -> None:
    trail_files = sorted(TRAILS_DIR.glob("*.json"))
    if not trail_files:
        raise FileNotFoundError(f"No trails in {TRAILS_DIR} - run build_trails first")

    print("Loading forest polygon index...")
    forest_index = ForestIndex()
    print(f"  {len(forest_index.polygons)} forest/wood polygons indexed")

    # Resume: load any prior partial output and skip already-processed trails
    output: dict = {}
    if OUTPUT_PATH.exists():
        output = yaml.safe_load(OUTPUT_PATH.read_text()) or {}
        if output:
            print(f"Resuming: {len(output)} trails already processed in {OUTPUT_PATH}")

    print(f"Auto-enriching up to {len(trail_files)} trails (one Overpass query each)")
    started = time.time()
    for i, tp in enumerate(trail_files, 1):
        trail = json.loads(tp.read_text())
        if trail["id"] in output:
            continue
        editorial = enrich_trail(trail, forest_index)
        output[trail["id"]] = editorial
        # Write after every trail so progress survives crashes / timeouts
        OUTPUT_PATH.write_text(yaml.safe_dump(output, sort_keys=False, default_flow_style=False))
        print(
            f"  [{i:3d}/{len(trail_files)}] {trail['name'][:50]:50s}  "
            f"scenery={editorial['scenery_tags']}  parking={editorial['parking']}  "
            f"exposure={editorial['exposure']}"
        )
        time.sleep(RATE_LIMIT_SEC)

    elapsed = time.time() - started
    print(f"\nWrote {len(output)} entries to {OUTPUT_PATH} (this run: {elapsed:.0f}s)")


if __name__ == "__main__":
    main()
