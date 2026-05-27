"""Pull State Trail segments for the 6-county area from WI DNR ArcGIS REST.

State trails are multi-use recreational corridors (often rail-to-trail conversions).
Each trail's permitted activities are encoded in per-activity Y/N/U flag fields.
"""

import json
from pathlib import Path

import requests

DNR_URL = (
    "https://dnrmaps.wi.gov/arcgis/rest/services/LF_DML/"
    "LF_DNR_MGD_Recreational_Opp_WTM_Ext/MapServer/1/query"
)
USER_AGENT = "wpr-trails/0.1 (https://github.com/RowanFlynnPilot/wpr-trails)"
# (west, south, east, north) - 11-county bbox.
BBOX = (-91.00, 44.25, -88.00, 46.00)

PARAMS = {
    "geometry": ",".join(str(v) for v in BBOX),
    "geometryType": "esriGeometryEnvelope",
    "inSR": "4326",
    "spatialRel": "esriSpatialRelIntersects",
    "outFields": ",".join([
        "OBJECTID",
        "PROP_NAME",
        "TRAIL_SEG_NAME",
        "COUNTY_NAME",
        "LENGTH_MI",
        "SURFACE_TYPE",
        "WALK_HIKE_CODE",
        "SNOWMO_CODE",
        "SNOWSHOE_CODE",
        "XSKI_GRMCL_CODE",
        "XSKI_GRMSK_CODE",
        "XSKI_UNGRM_CODE",
        "BIKE_OFFRD_CODE",
        "HORSE_CODE",
        "ATV_WINTER_CODE",
    ]),
    "returnGeometry": "true",
    "outSR": "4326",
    "f": "geojson",
}

OUTPUT_PATH = Path("data/raw/dnr_state_trails.geojson")


def fetch() -> dict:
    response = requests.get(
        DNR_URL,
        params=PARAMS,
        headers={"User-Agent": USER_AGENT},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    fc = fetch()
    features = fc.get("features", [])
    if not features:
        raise RuntimeError("DNR returned no State Trail features")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(fc, indent=2))
    print(f"Wrote {len(features)} State Trail features to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
