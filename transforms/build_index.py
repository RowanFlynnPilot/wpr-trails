"""Generate the slim index.json from current trail files.

Called by build_trails (after initial build), enrich_elevation (after
elevation fields populated), and enrich_trailheads (after trailheads
snapped). Single source of truth for index shape.

Also bakes a few filter-useful editorial fields into the index so the
frontend can filter on scenery, dog policy, family-friendliness, etc.
without fetching every per-trail JSON. Geometry stays in per-trail
JSONs (too large for the index).
"""

import json
from pathlib import Path

import yaml

EDITORIAL_PATH = Path("data/editorial.yaml")
EDITORIAL_AUTO_PATH = Path("data/editorial_auto.yaml")

# Editorial fields surfaced in index.json for filtering. Anything not in
# this list stays in per-trail JSONs only.
INDEX_EDITORIAL_FIELDS = (
    "scenery_tags",
    "dog_policy",
    "family_friendly",
    "exposure",
    "mud_susceptibility",
    "accessibility",
)


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def _merge_editorial(trail_id: str, auto: dict, human: dict) -> dict:
    """Same per-field cascade as build_scores.load_editorial_for_trail."""
    auto_block = auto.get(trail_id, {})
    auto_clean = {k: v for k, v in auto_block.items() if not k.startswith("_")}
    human_block = human.get(trail_id, {})
    return {**auto_clean, **human_block}


def write_index(trails_dir: Path, index_path: Path) -> None:
    editorial = _load_yaml(EDITORIAL_PATH)
    editorial_auto = _load_yaml(EDITORIAL_AUTO_PATH)

    index = []
    for trail_path in sorted(trails_dir.glob("*.json")):
        t = json.loads(trail_path.read_text())
        attrs = t["attributes"]
        merged_editorial = _merge_editorial(t["id"], editorial_auto, editorial)
        editorial_slim = {
            field: merged_editorial.get(field)
            for field in INDEX_EDITORIAL_FIELDS
        }
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
            "editorial": editorial_slim,
        })
    index_path.write_text(json.dumps(index, indent=2))
