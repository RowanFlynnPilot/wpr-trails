"""Pull USDA SSURGO soil data for every built trail.

For each trail in data/processed/trails/, asks the USDA Soil Data Access
service which soil map units the trail line crosses, then bulk-fetches the
drainage class and hydrologic group of the dominant component of each unique
mukey. Writes the result to data/raw/ssurgo.json.

The downstream transform (enrich_editorial_auto) uses these to replace the
placeholder "moderate" / "loamy" defaults on mud_susceptibility and drainage.

API used: SDA tabular service. Two query types:
  1) SDA_Get_Mukey_from_intersection_with_WktWgs84(<LINESTRING WKT>)
     - one call per trail, returns mukeys the line touches
  2) bulk component lookup for all unique mukeys, dominant component only

Both are POST against:
  https://sdmdataaccess.sc.egov.usda.gov/Tabular/SDMTabularService/post.rest

Trail geometry is already in EPSG:4326 (WGS84) so we can feed coordinates to
the SDA function directly.
"""

import json
import time
from pathlib import Path

import requests

SDA_URL = "https://sdmdataaccess.sc.egov.usda.gov/Tabular/SDMTabularService/post.rest"
USER_AGENT = "wpr-trails/0.1 (https://github.com/RowanFlynnPilot/wpr-trails)"

TRAILS_DIR = Path("data/processed/trails")
OUTPUT_PATH = Path("data/raw/ssurgo.json")

RATE_LIMIT_SEC = 1.0     # polite pause between per-trail SDA calls
TIMEOUT_SEC = 60         # per-request timeout; per-trail queries are typically <1s


def _post(query: str) -> list:
    """POST a SQL query to SDA, return the Table rows."""
    res = requests.post(
        SDA_URL,
        data={"query": query, "format": "JSON"},
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT_SEC,
    )
    res.raise_for_status()
    body = res.json()
    return body.get("Table", []) or []


def _line_wkt(geom: dict) -> str:
    """Build a LINESTRING or MULTILINESTRING WKT from a trail geometry block."""
    if geom["type"] == "LineString":
        pts = ",".join(f"{lng} {lat}" for lng, lat in geom["coordinates"])
        return f"LINESTRING({pts})"
    if geom["type"] == "MultiLineString":
        parts = [
            "(" + ",".join(f"{lng} {lat}" for lng, lat in line) + ")"
            for line in geom["coordinates"]
        ]
        return f"MULTILINESTRING({','.join(parts)})"
    raise ValueError(f"Unexpected geometry type: {geom['type']}")


def fetch_trail_mukeys(trail: dict) -> list[str]:
    """Return the list of unique mukeys whose polygons the trail line crosses."""
    wkt = _line_wkt(trail["geometry"])
    q = f"SELECT * FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('{wkt}')"
    rows = _post(q)
    return sorted({row[0] for row in rows})


def fetch_mukey_info(mukeys: list[str]) -> dict[str, dict]:
    """For each mukey, return the dominant component's drainage class + hyd group.

    'Dominant' here means majcompflag='Yes', which SSURGO uses to flag the
    highest-percentage component within a map unit. A few mukeys have no
    component with majcompflag='Yes' (data quality issues); those fall back to
    the highest comppct_r component.
    """
    if not mukeys:
        return {}

    # Try majcompflag first.
    in_list = ",".join(f"'{m}'" for m in mukeys)
    q = f"""
    SELECT c.mukey, c.drainagecl, c.hydgrp, c.compname, c.comppct_r
    FROM component c
    WHERE c.mukey IN ({in_list})
      AND c.majcompflag = 'Yes'
    """
    rows = _post(q)

    # Pick the highest-percentage row per mukey (in case of ties among major
    # components — rare but happens).
    chosen: dict[str, dict] = {}
    for mukey, drainage, hyd, name, pct in rows:
        pct_i = int(pct) if pct is not None else 0
        prev = chosen.get(mukey)
        if prev is None or pct_i > prev["comppct"]:
            chosen[mukey] = {
                "drainage_class": drainage,
                "hyd_group": hyd,
                "dominant_component": name,
                "comppct": pct_i,
            }

    # Fallback for mukeys missing a majcompflag='Yes' row.
    missing = [m for m in mukeys if m not in chosen]
    if missing:
        in_list = ",".join(f"'{m}'" for m in missing)
        q2 = f"""
        SELECT c.mukey, c.drainagecl, c.hydgrp, c.compname, c.comppct_r
        FROM component c
        WHERE c.mukey IN ({in_list})
        """
        rows2 = _post(q2)
        for mukey, drainage, hyd, name, pct in rows2:
            pct_i = int(pct) if pct is not None else 0
            prev = chosen.get(mukey)
            if prev is None or pct_i > prev["comppct"]:
                chosen[mukey] = {
                    "drainage_class": drainage,
                    "hyd_group": hyd,
                    "dominant_component": name,
                    "comppct": pct_i,
                }

    # Drop the helper "comppct" before returning — provenance only.
    for v in chosen.values():
        v.pop("comppct", None)
    return chosen


def main() -> None:
    trail_files = sorted(TRAILS_DIR.glob("*.json"))
    if not trail_files:
        raise FileNotFoundError(f"No trails in {TRAILS_DIR} - run build_trails first")

    # Resume support: load any prior output, skip trails already fetched.
    output = {"trail_mukeys": {}, "mukey_info": {}}
    if OUTPUT_PATH.exists():
        prior = json.loads(OUTPUT_PATH.read_text())
        output["trail_mukeys"] = prior.get("trail_mukeys", {})
        output["mukey_info"] = prior.get("mukey_info", {})
        if output["trail_mukeys"]:
            print(f"Resuming: {len(output['trail_mukeys'])} trails already fetched")

    print(f"Fetching SSURGO mukeys for {len(trail_files)} trails")
    started = time.time()
    for i, tp in enumerate(trail_files, 1):
        trail = json.loads(tp.read_text())
        if trail["id"] in output["trail_mukeys"]:
            continue
        mukeys = fetch_trail_mukeys(trail)
        output["trail_mukeys"][trail["id"]] = mukeys
        print(f"  [{i:3d}/{len(trail_files)}] {trail['name'][:50]:50s}  {len(mukeys)} mukeys")
        # Write after every trail so progress survives crashes.
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(json.dumps(output))
        time.sleep(RATE_LIMIT_SEC)

    all_mukeys = sorted({m for lst in output["trail_mukeys"].values() for m in lst})
    print(f"\nFetching drainage info for {len(all_mukeys)} unique mukeys")
    output["mukey_info"] = fetch_mukey_info(all_mukeys)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2))

    elapsed = time.time() - started
    print(
        f"\nWrote {len(output['trail_mukeys'])} trails + "
        f"{len(output['mukey_info'])} mukeys to {OUTPUT_PATH} "
        f"(this run: {elapsed:.0f}s)"
    )


if __name__ == "__main__":
    main()
