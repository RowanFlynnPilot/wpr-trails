"""Generate the slim index.json from current trail files.

Called by build_trails (after initial build) and enrich_elevation (after
elevation fields populated). Single source of truth for index shape.
"""

import json
from pathlib import Path


def write_index(trails_dir: Path, index_path: Path) -> None:
    index = []
    for trail_path in sorted(trails_dir.glob("*.json")):
        t = json.loads(trail_path.read_text())
        attrs = t["attributes"]
        index.append({
            "id": t["id"],
            "name": t["name"],
            "activities": t["activities"],
            "counties": attrs["counties"],
            "length_m": attrs["length_m"],
            "elevation_gain_m": attrs["elevation_gain_m"],
            "elevation_max_m": attrs["elevation_max_m"],
            "difficulty_estimated": attrs["difficulty_estimated"],
            "centroid": t["derived"]["centroid"],
            "drive_minutes_from_wausau": t["derived"]["drive_minutes_from_wausau"],
            "trailhead_coords": t["derived"].get("trailhead_coords"),
        })
    index_path.write_text(json.dumps(index, indent=2))
