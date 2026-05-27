"""Pull 11-county polygon boundaries from Census TIGERweb.

Run once at repo setup (or after extending TARGET_COUNTIES). Output is
cached and reused by every transform.
"""

import json
from pathlib import Path

import requests

TIGER_URL = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
    "State_County/MapServer/13/query"
)
USER_AGENT = "wpr-trails/0.1 (https://github.com/RowanFlynnPilot/wpr-trails)"

TARGET_COUNTIES = (
    # Original 6-county core: Marathon (WPR home) + 5 contiguous neighbors
    "Marathon", "Lincoln", "Langlade", "Taylor", "Shawano", "Portage",
    # Expansion: day-trip + weekend radius from Wausau
    "Clark",   # west of Marathon — Clark County Forest + IAT
    "Wood",    # south of Marathon — Wisconsin Rapids, Mead WL Area
    "Oneida",  # north of Lincoln — Minocqua, Bearskin State Trail
    "Forest",  # northeast of Langlade — deep Northwoods, NF land
    "Price",   # west of Taylor — Northwoods extension
)

PARAMS = {
    "where": (
        "STATE='55' AND BASENAME IN ("
        + ",".join(f"'{c}'" for c in TARGET_COUNTIES)
        + ")"
    ),
    "outFields": "BASENAME,GEOID",
    "returnGeometry": "true",
    "outSR": "4326",
    "f": "geojson",
}

OUTPUT_PATH = Path("data/raw/county_boundaries.geojson")


def fetch() -> dict:
    response = requests.get(
        TIGER_URL,
        params=PARAMS,
        headers={"User-Agent": USER_AGENT},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    fc = fetch()
    features = fc.get("features", [])
    if len(features) != len(TARGET_COUNTIES):
        raise RuntimeError(
            f"Expected {len(TARGET_COUNTIES)} counties, got {len(features)}"
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(fc, indent=2))
    print(f"Wrote {len(features)} county polygons to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
