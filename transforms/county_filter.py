"""Map a geometry to which of the 6 target counties it intersects.

Loaded once at import; reused across thousands of trail evaluations.
"""

import json
from pathlib import Path

from shapely.geometry import shape
from shapely.prepared import prep

BOUNDARIES_PATH = Path("data/raw/county_boundaries.geojson")
County = str  # canonical lowercase: 'marathon' | 'lincoln' | ...


def _load_counties() -> dict:
    if not BOUNDARIES_PATH.exists():
        raise FileNotFoundError(
            f"{BOUNDARIES_PATH} missing - run scrapers/county_boundaries.py first"
        )
    fc = json.loads(BOUNDARIES_PATH.read_text())
    return {
        f["properties"]["BASENAME"].lower(): prep(shape(f["geometry"]))
        for f in fc["features"]
    }


_COUNTIES = _load_counties()


def counties_for(geometry: dict) -> list:
    """Return sorted list of county slugs whose polygon intersects the geometry."""
    geom = shape(geometry)
    if geom.is_empty:
        raise ValueError("Empty geometry passed to counties_for")
    return sorted(c for c, poly in _COUNTIES.items() if poly.intersects(geom))
