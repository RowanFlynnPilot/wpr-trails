"""Build schema-shaped Trail records from raw OSM + DNR sources.

Source precedence: DNR State Trails > DNR Ice Age Trail > OSM hiking routes.
OSM relations that duplicate DNR-authoritative trails are dropped.

Outputs one JSON per trail to data/processed/trails/{id}.json
plus a slim index at data/processed/index.json.
"""

import json
import math
import re
from pathlib import Path
from typing import Iterable

from shapely.geometry import LineString, mapping, shape
from shapely.ops import linemerge, unary_union

from transforms.county_filter import counties_for
from transforms.build_index import write_index

OSM_RAW = Path("data/raw/osm_hiking_routes.json")
DNR_IAT_RAW = Path("data/raw/dnr_ice_age.geojson")
DNR_STATE_RAW = Path("data/raw/dnr_state_trails.geojson")
TRAILS_DIR = Path("data/processed/trails")
INDEX_PATH = Path("data/processed/index.json")

WAUSAU_LAT, WAUSAU_LNG = 44.9591, -89.6301
SINUOSITY = 1.3
AVG_SPEED_MPH = 50


# --- helpers ---------------------------------------------------------------

def slugify(name: str) -> str:
    s = re.sub(r"[^\w\s-]", "", name.lower())
    s = re.sub(r"[\s_]+", "-", s).strip("-")
    return s


def haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def drive_minutes(lng: float, lat: float) -> int:
    miles = haversine_miles(WAUSAU_LAT, WAUSAU_LNG, lat, lng) * SINUOSITY
    return round(miles / AVG_SPEED_MPH * 60)


def length_m(geom) -> float:
    if geom.geom_type == "LineString":
        parts = [list(geom.coords)]
    elif geom.geom_type == "MultiLineString":
        parts = [list(part.coords) for part in geom.geoms]
    else:
        raise ValueError(f"Unexpected geometry type: {geom.geom_type}")

    total = 0.0
    for line in parts:
        for (x1, y1), (x2, y2) in zip(line, line[1:]):
            mid_lat = (y1 + y2) / 2
            dx_m = (x2 - x1) * 111000 * math.cos(math.radians(mid_lat))
            dy_m = (y2 - y1) * 111000
            total += math.hypot(dx_m, dy_m)
    return total


def merge_lines(lines: list):
    """Union + linemerge that handles the single-line case shapely chokes on."""
    unioned = unary_union(lines)
    return linemerge(unioned) if unioned.geom_type == "MultiLineString" else unioned


def derive_state_trail_activities(props: dict) -> list:
    """Map DNR Y/N/U activity flags to our canonical activities list."""
    activities = []
    if props.get("WALK_HIKE_CODE") == "Y":
        activities.append("hiking")
    if props.get("SNOWSHOE_CODE") == "Y":
        activities.append("snowshoe")
    if any(props.get(f) == "Y" for f in
           ("XSKI_GRMCL_CODE", "XSKI_GRMSK_CODE", "XSKI_UNGRM_CODE")):
        activities.append("xc_ski")
    if props.get("SNOWMO_CODE") == "Y":
        activities.append("snowmobile")
    if props.get("BIKE_OFFRD_CODE") == "Y":
        activities.append("biking")
    if props.get("HORSE_CODE") == "Y":
        activities.append("horseback")
    # ATV access on a state trail also permits UTVs by WI 2014 statute
    # (the legal definitions overlap — most trails open to one open to both).
    if props.get("ATV_WINTER_CODE") == "Y":
        activities.extend(["atv", "utv"])
    return activities


def is_osm_duplicate(osm_name: str, state_trail_names: set) -> bool:
    """Drop OSM relations that duplicate DNR-authoritative records.

    - Exact (case-insensitive) match against State Trail PROP_NAMEs
    - IAT 'Segment' relations duplicate DNR IAT layer entries
    - IAT 'connector' relations are kept (DNR doesn't track between-segment gaps)
    """
    n = osm_name.lower()
    if n in {s.lower() for s in state_trail_names}:
        return True
    if ("ice age" in n or n.startswith("iat -") or n.startswith("iat-")) and "segment" in n:
        return True
    return False


# --- DNR State Trail -> Trail (group by PROP_NAME) -------------------------

def build_from_dnr_state_trails(fc: dict) -> Iterable[dict]:
    by_trail: dict = {}
    for feat in fc["features"]:
        name = (feat["properties"].get("PROP_NAME") or "").strip()
        if not name:
            continue
        by_trail.setdefault(name, []).append(feat)

    for name, feats in by_trail.items():
        lines = [shape(f["geometry"]) for f in feats]
        merged = merge_lines(lines)
        centroid = merged.centroid
        geom_mapping = mapping(merged)

        # Activity codes are typically uniform per trail; sample the first feature
        props_sample = feats[0]["properties"]
        activities = derive_state_trail_activities(props_sample)
        if not activities:
            continue  # if no activity is 'Y', this trail isn't relevant to our app

        yield {
            "id": f"state-{slugify(name)}",
            "name": name,
            "activities": activities,
            "sources": {
                "dnr": {
                    "object_ids": [f["properties"]["OBJECTID"] for f in feats],
                    "layer": "state_trail",
                    "last_fetched": "",
                }
            },
            "geometry": geom_mapping,
            "attributes": {
                "length_m": round(length_m(merged), 1),
                "elevation_gain_m": None,
                "elevation_max_m": None,
                "elevation_min_m": None,
                "elevation_profile": None,
                "difficulty_estimated": None,
                "surface": [],   # SURFACE_TYPE empty in current DNR data; editorial fills
                "is_loop": False,  # state trails are linear rail-to-trails
                "osm_network_class": None,
                "blaze_color": None,
                "counties": counties_for(geom_mapping),
                "park": None,
                "managing_authority": "WI DNR",
            },
            "editorial": {},
            "derived": {
                "centroid": [centroid.x, centroid.y],
                "bbox": list(merged.bounds),
                "drive_minutes_from_wausau": drive_minutes(centroid.x, centroid.y),
                "trailhead_coords": None,
            },
        }


# --- DNR IAT -> Trail (group by SEGMENT_NAME_TEXT) -------------------------

def build_from_dnr_iat(fc: dict) -> Iterable[dict]:
    by_segment: dict = {}
    for feat in fc["features"]:
        name = (feat["properties"].get("SEGMENT_NAME_TEXT") or "").strip()
        if not name:
            continue
        by_segment.setdefault(name, []).append(feat)

    for name, feats in by_segment.items():
        lines = [shape(f["geometry"]) for f in feats]
        merged = merge_lines(lines)
        centroid = merged.centroid
        geom_mapping = mapping(merged)

        yield {
            "id": f"iat-{slugify(name)}",
            "name": f"Ice Age Trail - {name}",
            "activities": ["hiking", "snowshoe"],
            "sources": {
                "dnr": {
                    "object_ids": [f["properties"]["OBJECTID"] for f in feats],
                    "layer": "ice_age",
                    "last_fetched": "",
                }
            },
            "geometry": geom_mapping,
            "attributes": {
                "length_m": round(
                    sum(f["properties"].get("LENGTH_METER_AMT", 0) for f in feats), 1
                ),
                "elevation_gain_m": None,
                "elevation_max_m": None,
                "elevation_min_m": None,
                "elevation_profile": None,
                "difficulty_estimated": None,
                "surface": [],
                "is_loop": False,
                "osm_network_class": "nwn",
                "blaze_color": "yellow",
                "counties": counties_for(geom_mapping),
                "park": None,
                "managing_authority": "IATA / WI DNR",
            },
            "editorial": {},
            "derived": {
                "centroid": [centroid.x, centroid.y],
                "bbox": list(merged.bounds),
                "drive_minutes_from_wausau": drive_minutes(centroid.x, centroid.y),
                "trailhead_coords": None,
            },
        }


# --- OSM relations -> Trail (after dedup against DNR sources) --------------

def build_from_osm(elements: list, state_trail_names: set) -> Iterable[dict]:
    for rel in (e for e in elements if e["type"] == "relation"):
        tags = rel.get("tags", {})
        name = tags.get("name")
        if not name:
            continue
        if is_osm_duplicate(name, state_trail_names):
            continue

        lines = []
        for member in rel.get("members", []):
            if member.get("type") != "way":
                continue
            geom = member.get("geometry") or []
            if len(geom) >= 2:
                lines.append(LineString([(pt["lon"], pt["lat"]) for pt in geom]))
        if not lines:
            continue

        merged = merge_lines(lines)
        centroid = merged.centroid
        geom_mapping = mapping(merged)

        yield {
            "id": f"osm-{slugify(name)}",
            "name": name,
            "activities": ["hiking"],
            "sources": {
                "osm": {"relation_id": rel["id"], "last_fetched": ""}
            },
            "geometry": geom_mapping,
            "attributes": {
                "length_m": round(length_m(merged), 1),
                "elevation_gain_m": None,
                "elevation_max_m": None,
                "elevation_min_m": None,
                "elevation_profile": None,
                "difficulty_estimated": None,
                "surface": [],
                "is_loop": tags.get("roundtrip") == "yes",
                "osm_network_class": tags.get("network"),
                "blaze_color": tags.get("colour") or tags.get("color"),
                "counties": counties_for(geom_mapping),
                "park": None,
                "managing_authority": tags.get("operator") or "Unknown",
            },
            "editorial": {},
            "derived": {
                "centroid": [centroid.x, centroid.y],
                "bbox": list(merged.bounds),
                "drive_minutes_from_wausau": drive_minutes(centroid.x, centroid.y),
                "trailhead_coords": None,
            },
        }


# --- OSM named ways -> Trail -----------------------------------------------
# Catches trails that are mapped in OSM as individual named ways rather than
# as a `route=hiking` relation. Common pattern in county forests (Clark,
# Wood, Northwoods) where local mappers tag the way with a name but never
# bundled it into a route relation.

OSM_NAMED_PATHS_RAW = Path("data/raw/osm_named_paths.json")

# Names ending in any of these strings are road segments tagged
# highway=track, not hiking trails.
ROAD_NAME_SUFFIXES = (
    " road", " rd", " rd.",
    " street", " st", " st.",
    " avenue", " ave", " ave.",
    " boulevard", " blvd",
    " lane", " ln", " ln.",
    " drive", " dr", " dr.",
    " highway", " hwy",
    " court", " ct", " ct.",
    " way",   # avenues-and-ways pattern; "trail" / "loop" still pass
)

MIN_WAY_LENGTH_M = 1000  # below this, more likely a sidewalk / connector than a trail


def _looks_like_road(name: str) -> bool:
    """Quick heuristic: name suffixed with a road-class word."""
    n = name.lower().rstrip()
    return any(n.endswith(suf) for suf in ROAD_NAME_SUFFIXES)


def derive_named_way_activities(tags: dict) -> list:
    """Activity list for a single OSM way based on access tags + name patterns.

    Motorized detection (ATV/UTV/snowmobile) comes from BOTH tags and name
    because OSM mappers in central WI often mark vehicle access only in the
    way name (e.g. "Flambeau ATV Trail 101", "Bakerville Snow Rovers
    Snowmobile Trail") rather than via the formal atv= / snowmobile= tags.
    """
    activities = []
    highway = tags.get("highway")
    name_upper = (tags.get("name") or "").upper()

    # Motorized first — these trump the highway=track hiking fallback below.
    is_atv = (
        tags.get("atv") in ("yes", "designated")
        or "ATV TRAIL" in name_upper
        or " ATV " in f" {name_upper} "
    )
    is_snowmobile = (
        tags.get("snowmobile") in ("yes", "designated")
        or "SNOWMOBILE" in name_upper
    )
    is_utv = "UTV" in name_upper  # OSM has no utv tag; name-only signal

    if is_atv:
        # WI 2014 statute: ATV trails legally permit UTVs (and vice versa),
        # so we tag both for filter completeness even when only one side is
        # mentioned.
        activities.extend(["atv", "utv"])
    elif is_utv:
        activities.extend(["utv", "atv"])
    if is_snowmobile:
        activities.append("snowmobile")

    # Non-motorized
    if highway in ("path", "footway") or tags.get("foot") in ("yes", "designated"):
        activities.append("hiking")
    if tags.get("bicycle") in ("yes", "designated"):
        activities.append("biking")
    if tags.get("horse") in ("yes", "designated"):
        activities.append("horseback")
    if tags.get("ski") in ("yes", "designated") or tags.get("piste:type") == "nordic":
        activities.append("xc_ski")

    # Fallback: generic tracks default to hiking ONLY when no motorized
    # indicator was found and foot isn't explicitly excluded. Previously
    # this fired even for ATV-named tracks, which mistakenly surfaced
    # motorized routes in the hiking filter.
    if (
        not activities
        and highway == "track"
        and tags.get("foot") != "no"
    ):
        activities.append("hiking")

    return sorted(set(activities))


def build_from_osm_named_ways(
    elements: list,
    excluded_names: set,
) -> Iterable[dict]:
    """Group ways by name, merge geometry, yield trail records.

    excluded_names: lowercased names already covered by State Trail or OSM
    relation sources, to avoid double-counting popular trails that exist in
    both forms.
    """
    by_name: dict = {}
    for el in elements:
        if el.get("type") != "way":
            continue
        tags = el.get("tags") or {}
        name = tags.get("name")
        if not name:
            continue
        if name.lower() in excluded_names:
            continue
        if _looks_like_road(name):
            continue
        geom = el.get("geometry") or []
        if len(geom) < 2:
            continue
        by_name.setdefault(name, []).append(el)

    for name, ways in by_name.items():
        lines = [
            LineString([(pt["lon"], pt["lat"]) for pt in w["geometry"]])
            for w in ways
        ]
        merged = merge_lines(lines)
        total_len = length_m(merged)
        if total_len < MIN_WAY_LENGTH_M:
            continue
        centroid = merged.centroid
        geom_mapping = mapping(merged)

        # Sample tags from the first way for activity derivation. Multiple
        # ways with the same name nearly always share access tags.
        sample_tags = ways[0].get("tags") or {}
        activities = derive_named_way_activities(sample_tags)
        if not activities:
            continue

        yield {
            "id": f"osmway-{slugify(name)}",
            "name": name,
            "activities": sorted(set(activities)),
            "sources": {
                "osm": {
                    "way_ids": [w["id"] for w in ways],
                    "kind": "named_way",
                    "last_fetched": "",
                }
            },
            "geometry": geom_mapping,
            "attributes": {
                "length_m": round(total_len, 1),
                "elevation_gain_m": None,
                "elevation_max_m": None,
                "elevation_min_m": None,
                "elevation_profile": None,
                "difficulty_estimated": None,
                "surface": [sample_tags["surface"]] if sample_tags.get("surface") else [],
                "is_loop": False,
                "osm_network_class": sample_tags.get("network"),
                "blaze_color": sample_tags.get("colour") or sample_tags.get("color"),
                "counties": counties_for(geom_mapping),
                "park": None,
                "managing_authority": sample_tags.get("operator") or "Unknown",
            },
            "editorial": {},
            "derived": {
                "centroid": [centroid.x, centroid.y],
                "bbox": list(merged.bounds),
                "drive_minutes_from_wausau": drive_minutes(centroid.x, centroid.y),
                "trailhead_coords": None,
            },
        }


# --- Main -------------------------------------------------------------------

def main() -> None:
    for path in (OSM_RAW, DNR_IAT_RAW, DNR_STATE_RAW):
        if not path.exists():
            raise FileNotFoundError(f"{path} missing - run the corresponding scraper")

    osm_data = json.loads(OSM_RAW.read_text())
    dnr_iat = json.loads(DNR_IAT_RAW.read_text())
    dnr_state = json.loads(DNR_STATE_RAW.read_text())
    named_paths = (
        json.loads(OSM_NAMED_PATHS_RAW.read_text())
        if OSM_NAMED_PATHS_RAW.exists()
        else {"elements": []}
    )

    # State Trail names feed the OSM relation dedup pass
    state_trail_names = {
        f["properties"]["PROP_NAME"]
        for f in dnr_state["features"]
        if f["properties"].get("PROP_NAME")
    }

    trails: list = []
    trails.extend(build_from_dnr_state_trails(dnr_state))
    trails.extend(build_from_dnr_iat(dnr_iat))
    trails.extend(build_from_osm(osm_data.get("elements", []), state_trail_names))

    # Named-way pass: exclude anything already represented above by name
    excluded_for_ways = {t["name"].lower() for t in trails}
    # Also exclude IAT prefixed names — every IAT segment way also has the
    # full route name "Ice Age Trail" set, which we don't want a second time
    excluded_for_ways.add("ice age trail")
    trails.extend(
        build_from_osm_named_ways(named_paths.get("elements", []), excluded_for_ways)
    )

    # Drop trails whose geometry doesn't intersect any target county
    trails = [t for t in trails if t["attributes"]["counties"]]

    TRAILS_DIR.mkdir(parents=True, exist_ok=True)
    # Clear stale records first so renamed/dropped trails don't linger
    for old in TRAILS_DIR.glob("*.json"):
        old.unlink()
    for t in trails:
        (TRAILS_DIR / f"{t['id']}.json").write_text(json.dumps(t, indent=2))

    write_index(TRAILS_DIR, INDEX_PATH)

    # Summary
    by_source = {"state": 0, "iat": 0, "osm": 0, "osmway": 0}
    for t in trails:
        prefix = t["id"].split("-")[0]
        by_source[prefix] = by_source.get(prefix, 0) + 1
    print(f"Built {len(trails)} trails -> {TRAILS_DIR}")
    print(f"  State Trails:        {by_source['state']}")
    print(f"  IAT segments:        {by_source['iat']}")
    print(f"  OSM relations:       {by_source['osm']}")
    print(f"  OSM named ways:      {by_source['osmway']}")


if __name__ == "__main__":
    main()
