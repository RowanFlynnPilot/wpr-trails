"""Pull Ice Age Trail segments for the 6-county area from WI DNR ArcGIS REST."""

import json
import time
from pathlib import Path

import requests

DNR_URL = (
    "https://dnrmaps.wi.gov/arcgis/rest/services/LF_DML/"
    "LF_DNR_MGD_Recreational_Opp_WTM_Ext/MapServer/2/query"
)
USER_AGENT = "wpr-trails/0.1 (https://github.com/RowanFlynnPilot/wpr-trails)"

# (west, south, east, north) - ArcGIS envelope order in EPSG:4326.
# 11-county bbox; see scrapers/county_boundaries.py for the full list.
BBOX = (-91.00, 44.25, -88.00, 46.00)

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


MAX_RETRIES = 4
BACKOFF_SEC = 15.0  # WI DNR ArcGIS recovers from 500s within seconds; this is generous


def fetch() -> dict:
    """GET with retry. WI DNR's ArcGIS endpoint returns transient 500s
    under load — happened once during weekly-pipeline run 26552790443.
    """
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(
                DNR_URL,
                params=PARAMS,
                headers={"User-Agent": USER_AGENT},
                timeout=90,
            )
            if response.status_code in (500, 502, 503, 504):
                last_err = f"HTTP {response.status_code}"
                print(
                    f"  WI DNR returned {response.status_code} on attempt "
                    f"{attempt}/{MAX_RETRIES}; sleeping {BACKOFF_SEC:.0f}s",
                    flush=True,
                )
                time.sleep(BACKOFF_SEC)
                continue
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            last_err = str(exc)
            if attempt == MAX_RETRIES:
                break
            print(
                f"  WI DNR request errored on attempt {attempt}/{MAX_RETRIES}: "
                f"{exc}; sleeping {BACKOFF_SEC:.0f}s",
                flush=True,
            )
            time.sleep(BACKOFF_SEC)
    raise RuntimeError(
        f"WI DNR Ice Age Trail endpoint failed after {MAX_RETRIES} attempts: {last_err}"
    )


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
