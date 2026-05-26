"""Pull active NWS alerts for the 6-county area.

Used downstream to:
  - Drop affected trails from rankings (flood warnings -> close low-lying trails)
  - Surface advisories alongside the conditions card on the frontend

NWS zone codes for the 6 counties were verified at:
https://api.weather.gov/zones?type=county&area=WI
"""

import json
from pathlib import Path

import requests

USER_AGENT = "wpr-trails/0.1 (https://github.com/RowanFlynnPilot/wpr-trails)"

# County-zone codes for the 6 target counties (verified against NWS zone catalog)
COUNTY_ZONES = {
    "marathon": "WIC073",
    "lincoln":  "WIC069",
    "langlade": "WIC067",
    "taylor":   "WIC119",
    "shawano":  "WIC115",
    "portage":  "WIC097",
}

ALERTS_URL = "https://api.weather.gov/alerts/active"
OUTPUT_PATH = Path("data/raw/nws_alerts.json")


def fetch() -> dict:
    response = requests.get(
        ALERTS_URL,
        params={"zone": ",".join(COUNTY_ZONES.values())},
        headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    data = fetch()
    features = data.get("features", [])
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(data, indent=2))
    print(f"Wrote {len(features)} active alerts to {OUTPUT_PATH}")
    for f in features[:5]:
        p = f["properties"]
        print(f"  {p.get('event'):30s} severity={p.get('severity')}  areas={p.get('areaDesc','')[:60]}")


if __name__ == "__main__":
    main()
