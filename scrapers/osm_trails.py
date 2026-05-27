"""Pull named hiking-route relations for the 6-county area from OSM via Overpass."""

import json
from pathlib import Path

import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "wpr-trails/0.1 (https://github.com/RowanFlynnPilot/wpr-trails)"

# (south, west, north, east) — 11-county bbox:
# Marathon, Lincoln, Langlade, Taylor, Shawano, Portage,
# Clark, Wood, Oneida, Forest, Price
BBOX = (44.25, -91.00, 46.00, -88.00)

QUERY = f"""
[out:json][timeout:120];
relation["route"="hiking"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
out body geom;
"""

OUTPUT_PATH = Path("data/raw/osm_hiking_routes.json")


def fetch() -> dict:
    response = requests.post(
        OVERPASS_URL,
        data={"data": QUERY},
        headers={"User-Agent": USER_AGENT},
        timeout=180,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    payload = fetch()
    elements = payload.get("elements", [])
    if not elements:
        raise RuntimeError("Overpass returned no elements - query or service issue")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {len(elements)} OSM elements to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
