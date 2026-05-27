"""Pull OSM forest/wood polygons in the 6-county bbox for exposure derivation.

Used by transforms/enrich_editorial_auto.py to determine whether a trail's
sample points fall under forest canopy. One-time fetch; cache locally.
"""

import json
from pathlib import Path

import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "wpr-trails/0.1 (https://github.com/RowanFlynnPilot/wpr-trails)"

# 11-county bbox (south, west, north, east):
# Marathon + Lincoln + Langlade + Taylor + Shawano + Portage
# + Clark + Wood + Oneida + Forest + Price
BBOX = (44.25, -91.00, 46.00, -88.00)

QUERY = f"""
[out:json][timeout:240];
(
  way["landuse"="forest"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  way["natural"="wood"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  relation["landuse"="forest"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  relation["natural"="wood"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
);
out geom;
"""

OUTPUT_PATH = Path("data/raw/osm_forest.json")


def fetch() -> dict:
    response = requests.post(
        OVERPASS_URL,
        data={"data": QUERY},
        headers={"User-Agent": USER_AGENT},
        timeout=300,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    payload = fetch()
    elements = payload.get("elements", [])
    if not elements:
        raise RuntimeError("Overpass returned no forest polygons")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload))   # compact - this file is large
    size_mb = OUTPUT_PATH.stat().st_size / 1024 / 1024
    print(f"Wrote {len(elements)} forest/wood polygons ({size_mb:.1f}MB) to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
