"""Spatial index of OSM forest/wood polygons; fast point-in-polygon checks.

Used by transforms/enrich_editorial_auto.py to determine what fraction of a
trail's sample points fall under forest canopy.
"""

import json
from pathlib import Path

from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.strtree import STRtree

FOREST_PATH = Path("data/raw/osm_forest.json")


def _ways_to_polygons(elements: list) -> list:
    """Convert OSM ways/relations with 'geometry' into shapely polygons.

    Ways: a single closed line -> Polygon.
    Relations: multipolygon members -> MultiPolygon.
    """
    polygons = []
    for el in elements:
        if el["type"] == "way":
            coords = [(pt["lon"], pt["lat"]) for pt in el.get("geometry", [])]
            if len(coords) >= 4 and coords[0] == coords[-1]:
                polygons.append(Polygon(coords))
        elif el["type"] == "relation":
            rings = []
            for member in el.get("members", []):
                geom = member.get("geometry") or []
                if len(geom) >= 4:
                    coords = [(pt["lon"], pt["lat"]) for pt in geom]
                    if coords[0] == coords[-1]:
                        rings.append(coords)
            if rings:
                polys = [Polygon(r) for r in rings if len(r) >= 4]
                if len(polys) == 1:
                    polygons.append(polys[0])
                elif len(polys) > 1:
                    polygons.append(MultiPolygon(polys))
    return polygons


class ForestIndex:
    """Spatial index of all forest/wood polygons in the 6-county bbox.

    Built once at the start of enrichment, reused across all trails.
    """

    def __init__(self):
        if not FOREST_PATH.exists():
            raise FileNotFoundError(
                f"{FOREST_PATH} missing - run scrapers/osm_landcover.py first"
            )
        data = json.loads(FOREST_PATH.read_text())
        self.polygons = _ways_to_polygons(data["elements"])
        self.tree = STRtree(self.polygons)

    def coverage(self, sample_points: list) -> float:
        """Fraction of (lng, lat) points falling inside any forest polygon."""
        if not sample_points:
            raise ValueError("No sample points provided to ForestIndex.coverage")
        inside = 0
        for lng, lat in sample_points:
            pt = Point(lng, lat)
            for idx in self.tree.query(pt):
                if self.polygons[idx].contains(pt):
                    inside += 1
                    break
        return inside / len(sample_points)
