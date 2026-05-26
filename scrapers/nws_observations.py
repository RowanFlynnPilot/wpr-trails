"""Fetch recent observations from KCWA (Central WI Airport) for precip totals.

KCWA is the nearest ASOS station to Wausau with reliable hourly precip reporting.
80 records = roughly 3+ days of hourly data, enough for 72h totals with margin.
"""

import json
from pathlib import Path

import requests

USER_AGENT = "wpr-trails/0.1 (https://github.com/RowanFlynnPilot/wpr-trails)"
STATION = "KCWA"
OBSERVATIONS_URL = f"https://api.weather.gov/stations/{STATION}/observations"
OUTPUT_PATH = Path("data/raw/nws_observations.json")


def fetch() -> dict:
    response = requests.get(
        OBSERVATIONS_URL,
        params={"limit": 80},
        headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    data = fetch()
    features = data.get("features", [])
    if not features:
        raise RuntimeError(f"No observations returned for {STATION}")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(data, indent=2))
    print(f"Wrote {len(features)} observations from {STATION} to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
