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
SSURGO_PATH = Path("data/raw/ssurgo.json")

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


def derive_dog_policy(trail: dict) -> tuple:
    """Wisconsin defaults: leashed dogs allowed on public hiking trails.

    Trail-managing authority drives the decision:
    - DNR / IATA / county-managed → leashed (matches by abbreviation OR full name)
    - "Unknown" authority → leashed too. In our 6-county scope, OSM trails
      without a DNR/IATA/county match are almost all on public land (state/
      county/town parks, NF land), and WI state law defaults to "leashed
      allowed unless signed otherwise" on public trails. The editorial
      override path catches the rare private-land exception.
    - Any other named authority we don't recognize → unknown (conservative)

    Returns (policy, provenance_note).
    """
    auth_raw = trail["attributes"].get("managing_authority") or "Unknown"
    auth = auth_raw.lower()

    leashed_markers = (
        "dnr",
        "department of natural resources",
        "iata",
        "ice age trail alliance",
        "county",
        "national forest",
        "us forest",
    )
    if any(m in auth for m in leashed_markers):
        return "leashed", f"WI public-land default; authority='{auth_raw}'"
    if auth == "unknown":
        return "leashed", (
            "WI public-land default; trail has no managing authority "
            "(OSM-only), assumed public per regional pattern"
        )
    return "unknown", f"unrecognized authority='{auth_raw}'"


def derive_accessibility(trail: dict) -> tuple:
    """Coarse terrain class — best we can do without OSM surface tags.

    Surface data is currently empty across all trails (DNR doesn't tag it,
    OSM is sparse), so 'wheelchair_easy' would be guesswork. Instead we
    classify terrain difficulty:

    - easy_terrain: easy difficulty + length < 1.5 mi + gain < 100 ft —
      suitable for less mobile visitors, walkers with strollers
    - rugged: difficult/strenuous OR gain > 1000 ft — needs sturdy boots
    - varied: everything else

    Returns (value, provenance_note). If/when surface tagging improves,
    a 'wheelchair_easy' tier can be added that requires paved/boardwalk.
    """
    diff = trail["attributes"].get("difficulty_estimated")
    miles = trail["attributes"]["length_m"] / 1609.34
    gain_ft = trail["attributes"]["elevation_gain_m"] * 3.281

    if diff == "easy" and miles < 1.5 and gain_ft < 100:
        return "easy_terrain", (
            f"easy / {miles:.1f}mi / {gain_ft:.0f}ft gain — gentle walking"
        )
    if diff in ("difficult", "strenuous") or gain_ft > 1000:
        return "rugged", f"diff={diff} / {gain_ft:.0f}ft gain"
    return "varied", f"diff={diff} / {miles:.1f}mi / {gain_ft:.0f}ft gain"


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


def derive_soil_fields(mukey_list: list, mukey_info: dict) -> tuple:
    """Map a trail's SSURGO mukeys to (mud_susceptibility, drainage, note).

    mud_susceptibility (one of low | moderate | high) drives the 25% mud_risk
    scoring weight. Threshold-based so a single poorly-drained mukey on a long
    trail doesn't flip the whole trail to high — but if a meaningful share
    (>=30%) of the trail crosses Somewhat-poorly-drained-or-worse soils, it
    does.

    drainage (sandy | loamy | clay) is a soil-texture proxy derived from
    hydrologic group, modal across the trail. Currently descriptive only —
    no scoring factor consumes it yet, but it's surfaced in the UI.
    """
    if not mukey_list:
        return "moderate", "loamy", "no SSURGO mukeys for this trail"

    drainage_classes = [
        mukey_info[mk]["drainage_class"]
        for mk in mukey_list
        if mk in mukey_info and mukey_info[mk]["drainage_class"]
    ]
    hyd_groups = [
        mukey_info[mk]["hyd_group"]
        for mk in mukey_list
        if mk in mukey_info and mukey_info[mk]["hyd_group"]
    ]

    if not drainage_classes:
        return "moderate", "loamy", f"no drainage data for {len(mukey_list)} mukeys"

    n = len(drainage_classes)
    counts = Counter(drainage_classes)
    poor = (
        counts.get("Very poorly drained", 0)
        + counts.get("Poorly drained", 0)
        + counts.get("Somewhat poorly drained", 0)
    )
    well = (
        counts.get("Excessively drained", 0)
        + counts.get("Somewhat excessively drained", 0)
        + counts.get("Well drained", 0)
    )
    if poor / n >= 0.30:
        mud = "high"
    elif well / n >= 0.70:
        mud = "low"
    else:
        mud = "moderate"

    drainage = _hyd_to_texture(hyd_groups)

    note = (
        f"SSURGO: {n} mukeys, "
        f"{poor} poorly-drained / {well} well-drained "
        f"(top class: {counts.most_common(1)[0][0]})"
    )
    return mud, drainage, note


def _hyd_to_texture(hyd_groups: list) -> str:
    """Modal texture across hydrologic group first-letters.

    Dual classifications (A/D, B/D, C/D) are wetland soils — sandy/loamy
    when drained, clay-like when waterlogged. We use the first letter for
    'normal conditions' texture; the mud_susceptibility logic above handles
    the wet-state behavior via drainage class.
    """
    if not hyd_groups:
        return "loamy"
    first_letters = [h[0] for h in hyd_groups if h and h[0] in "ABCD"]
    if not first_letters:
        return "loamy"
    letter_to_texture = {"A": "sandy", "B": "loamy", "C": "loamy", "D": "clay"}
    textures = [letter_to_texture[c] for c in first_letters]
    return Counter(textures).most_common(1)[0][0]


def derive_bike_allowed(trail: dict) -> bool:
    """State Trail layer carries this explicitly via activity codes; everything else conservative."""
    if trail["id"].startswith("state-"):
        # State trails default to multi-use unless the DNR codes said otherwise.
        # We don't currently carry BIKE_OFFRD_CODE through to the trail record,
        # but in central WI all 5 state trails in the bbox allow bikes per DNR data.
        return True
    return False


# --- Main -----------------------------------------------------------------

def enrich_trail(trail: dict, forest_index: ForestIndex, ssurgo: dict) -> dict:
    features = fetch_nearby_features(trail)
    forest_cov = forest_index.coverage(trail_sample_points(trail))

    scenery, scenery_counts = derive_scenery_tags(features)
    parking, n_parking = derive_parking(features)
    dog_policy, dog_note = derive_dog_policy(trail)
    exposure, exposure_note = derive_exposure(trail, forest_cov)
    family_friendly = derive_family_friendly(trail)
    seasonality = derive_seasonality(trail, scenery)
    bike_allowed = derive_bike_allowed(trail)
    accessibility, access_note = derive_accessibility(trail)

    trail_mukeys = ssurgo["trail_mukeys"].get(trail["id"], [])
    mud, drainage, soil_note = derive_soil_fields(trail_mukeys, ssurgo["mukey_info"])

    return {
        "family_friendly": family_friendly,
        "dog_policy": dog_policy,
        "bike_allowed": bike_allowed,
        "parking": parking,
        "accessibility": accessibility,
        "scenery_tags": scenery,
        "seasonality": seasonality,
        "mud_susceptibility": mud,
        "exposure": exposure,
        "drainage": drainage,
        "notes": None,
        "last_field_check": None,
        "validated": False,
        "_provenance": {
            "scenery_tags": f"OSM: {dict(scenery_counts)} features within {SEARCH_RADIUS_M}m",
            "parking": f"OSM: {n_parking} amenity=parking within {PARKING_RADIUS_M}m",
            "dog_policy": dog_note,
            "accessibility": access_note,
            "exposure": exposure_note,
            "family_friendly": (
                f"difficulty={trail['attributes'].get('difficulty_estimated')}, "
                f"length={trail['attributes']['length_m']/1609.34:.1f}mi"
            ),
            "seasonality": "derived from activities + scenery_tags",
            "bike_allowed": "state-trail default; others conservative=false",
            "mud_susceptibility": soil_note,
            "drainage": "modal soil texture from SSURGO hydrologic group",
        },
    }


def main() -> None:
    trail_files = sorted(TRAILS_DIR.glob("*.json"))
    if not trail_files:
        raise FileNotFoundError(f"No trails in {TRAILS_DIR} - run build_trails first")

    print("Loading forest polygon index...")
    forest_index = ForestIndex()
    print(f"  {len(forest_index.polygons)} forest/wood polygons indexed")

    if not SSURGO_PATH.exists():
        raise FileNotFoundError(
            f"{SSURGO_PATH} missing - run scrapers/usda_ssurgo.py first"
        )
    ssurgo = json.loads(SSURGO_PATH.read_text())
    print(
        f"  SSURGO: {len(ssurgo['trail_mukeys'])} trails, "
        f"{len(ssurgo['mukey_info'])} unique mukeys"
    )

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
        editorial = enrich_trail(trail, forest_index, ssurgo)
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
