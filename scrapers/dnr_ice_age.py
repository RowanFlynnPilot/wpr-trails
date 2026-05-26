"""Pull Ice Age Trail segments for the 6-county area from WI DNR ArcGIS REST."""

import json
from pathlib import Path

import requests

DNR_URL = (
    "https://dnrmaps.wi.gov/arcgis/rest/services/LF_DML/"
    "LF_DNR_MGD_Recreational_Opp_WTM_Ext/MapServer/2/query"
)
USER_AGENT = "wpr-trails/0.1 (https://github.com/RowanFlynnPilot/wpr-trails)"

# (west, south, east, north) - ArcGIS envelope order in EPSG:4326
BBOX = (-91.00, 44.25, -88.15, 45.75)

PARAMS = {
    "geometry": ",".join(str(v) for v in BBOX),
    "geometryType": "esriGeometryEnvelope",
    "inSR": "4326",
    "spatialRel": "esriSpatialRelIntersects",
    "outFields": ",".join([
        "OBJECTID",
        "SEGMENT_NAME_TEXT",
        "LENGTH_METER_AMT",
        "TRAIL_COMPLETION_STATUS_CODE",
        "NPS_CERTIFICATION_STATUS_CODE",
    ]),
    "returnGeometry": "true",
    "outSR": "4326",
    "f": "geojson",
}

OUTPUT_PATH = Path("data/raw/dnr_ice_age.geojson")


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
        raise RuntimeError("DNR returned no features - bbox or service issue")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(fc, indent=2))
    print(f"Wrote {len(features)} IAT segment features to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
