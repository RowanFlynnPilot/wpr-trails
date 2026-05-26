"""Fetch NWS forecast for the Wausau-area gridpoint."""

import json
from pathlib import Path

import requests

USER_AGENT = "wpr-trails/0.1 (https://github.com/RowanFlynnPilot/wpr-trails)"
# Gridpoint resolved once from https://api.weather.gov/points/44.9591,-89.6301
NWS_FORECAST_URL = "https://api.weather.gov/gridpoints/GRB/25,50/forecast"
OUTPUT_PATH = Path("data/raw/nws_forecast.json")


def fetch() -> dict:
    response = requests.get(
        NWS_FORECAST_URL,
        headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    data = fetch()
    periods = data.get("properties", {}).get("periods")
    if not periods:
        raise RuntimeError("NWS forecast missing periods")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(data, indent=2))
    print(f"Wrote forecast ({len(periods)} periods) to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
