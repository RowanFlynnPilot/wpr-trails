"""Pull individually-named hiking ways from OSM via Overpass.

Complements scrapers/osm_trails.py (which queries route relations). Many
real trails in the county-forest belt — Clark, Wood, and pockets in the
Northwoods — are mapped in OSM as a set of named highway=path / track /
footway ways rather than as a relation. Those slip past the relation
query but show up here.

Output: data/raw/osm_named_paths.json — raw Overpass response (way
elements with geom + tags). transforms/build_trails.py merges them by
name and drops duplicates against the existing relation/DNR sources.
"""

import json
from pathlib import Path

import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "wpr-trails/0.1 (https://github.com/RowanFlynnPilot/wpr-trails)"

# (south, west, north, east) — same 11-county bbox as the other OSM scrapers.
BBOX = (44.25, -91.00, 46.00, -88.00)

QUERY = f"""
[out:json][timeout:240];
(
  way[name][highway~"path|track|footway"]
    ({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
);
out body geom;
"""

OUTPUT_PATH = Path("data/raw/osm_named_paths.json")


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
        raise RuntimeError("Overpass returned no named-path ways - query or service issue")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload))
    size_mb = OUTPUT_PATH.stat().st_size / 1024 / 1024
    print(f"Wrote {len(elements)} named-path ways ({size_mb:.1f}MB) to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
