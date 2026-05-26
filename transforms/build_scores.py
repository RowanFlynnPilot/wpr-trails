"""Score every trail against current conditions; emit a ranked list.

Joins trails + conditions + editorial + active NWS alerts. Alerts in the
CLOSURE_EVENTS set whose polygons intersect a trail's geometry add that
trail's id to active_closure_ids, causing the scoring function to filter it out.
"""

import json
from pathlib import Path

import yaml
from shapely.geometry import shape
from shapely.prepared import prep

from transforms.score import score_trail

TRAILS_DIR = Path("data/processed/trails")
EDITORIAL_PATH = Path("data/editorial.yaml")
EDITORIAL_AUTO_PATH = Path("data/editorial_auto.yaml")
CONDITIONS_PATH = Path("data/processed/conditions.json")
ALERTS_PATH = Path("data/raw/nws_alerts.json")
OUTPUT_PATH = Path("data/processed/scores.json")

# Alert events that close affected trails outright. Other alert types
# (high wind, winter weather) flow through to the UI but don't filter.
CLOSURE_EVENTS = {
    "Flood Warning",
    "Flash Flood Warning",
    "Tornado Warning",
    "Tornado Emergency",
}


def load_editorial_for_trail(trail_id: str, editorial: dict, editorial_auto: dict) -> dict:
    """Per-field cascade: editorial.yaml (human) overrides editorial_auto.yaml (derived).

    A trail with no auto entry and no human entry returns {}, which the scoring
    function handles via its 'awaiting_field_check' filter.
    """
    auto_block = editorial_auto.get(trail_id, {})
    # Strip provenance from the merged block; it's metadata for humans.
    auto_clean = {k: v for k, v in auto_block.items() if not k.startswith("_")}
    human_block = editorial.get(trail_id, {})
    return {**auto_clean, **human_block}


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def compute_closures(trails: list, alerts_fc: dict) -> list:
    """Trail ids whose actual geometry intersects a closure-worthy alert polygon.

    Uses real line geometry rather than bbox to avoid false positives on long
    linear trails - a 76-mile state trail's bbox spans most of the region.

    Zone-only alerts (no geometry) are surfaced for display but not used
    for closures in v1 - too coarse to avoid false positives.
    """
    closure_ids = set()
    for alert in alerts_fc.get("features", []):
        event = alert["properties"].get("event")
        if event not in CLOSURE_EVENTS:
            continue
        geom = alert.get("geometry")
        if not geom:
            continue
        alert_poly = prep(shape(geom))
        for t in trails:
            if alert_poly.intersects(shape(t["geometry"])):
                closure_ids.add(t["id"])
    return sorted(closure_ids)


def main() -> None:
    if not CONDITIONS_PATH.exists():
        raise FileNotFoundError(f"{CONDITIONS_PATH} missing - run build_conditions.py")
    if not TRAILS_DIR.exists():
        raise FileNotFoundError(f"{TRAILS_DIR} missing - run build_trails.py")

    conditions = json.loads(CONDITIONS_PATH.read_text())
    editorial = load_yaml(EDITORIAL_PATH)
    editorial_auto = load_yaml(EDITORIAL_AUTO_PATH)
    alerts = json.loads(ALERTS_PATH.read_text()) if ALERTS_PATH.exists() else {"features": []}

    trails = []
    for tp in sorted(TRAILS_DIR.glob("*.json")):
        t = json.loads(tp.read_text())
        t["editorial"] = load_editorial_for_trail(t["id"], editorial, editorial_auto)
        trails.append(t)

    conditions["scoring_context"]["active_closure_ids"] = compute_closures(trails, alerts)

    default_prefs: dict = {}
    results = [score_trail(t, conditions, default_prefs) for t in trails]
    ranked = sorted(
        (r for r in results if not r["hard_filters_failed"]),
        key=lambda r: -r["score"],
    )
    filtered = [r for r in results if r["hard_filters_failed"]]

    output = {
        "computed_at": conditions["fetched_at"],
        "conditions_summary": conditions["scoring_context"],
        "active_alerts": [
            {
                "event": a["properties"].get("event"),
                "severity": a["properties"].get("severity"),
                "headline": a["properties"].get("headline"),
                "area_desc": a["properties"].get("areaDesc"),
                "ends": a["properties"].get("ends"),
            }
            for a in alerts.get("features", [])
        ],
        "ranked": ranked,
        "filtered_out": [
            {"trail_id": r["trail_id"], "name": r["name"], "reasons": r["hard_filters_failed"]}
            for r in filtered
        ],
    }

    OUTPUT_PATH.write_text(json.dumps(output, indent=2))

    closures = conditions["scoring_context"]["active_closure_ids"]
    print(f"Scored {len(results)} trails: {len(ranked)} ranked, {len(filtered)} filtered")
    if closures:
        print(f"  Closed by active alerts: {len(closures)}")


if __name__ == "__main__":
    main()
