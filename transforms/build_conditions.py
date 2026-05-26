"""Merge raw NWS forecast + observations into a single conditions record.

Output includes a `scoring_context` block shaped to feed transforms/score.py directly.
"""

import json
import math
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

NWS_FORECAST = Path("data/raw/nws_forecast.json")
NWS_OBSERVATIONS = Path("data/raw/nws_observations.json")
OUTPUT_PATH = Path("data/processed/conditions.json")

WAUSAU_LAT, WAUSAU_LNG = 44.9591, -89.6301
MM_PER_INCH = 25.4


def parse_wind_mph(wind_str: str) -> tuple:
    """Parse '6 to 10 mph' or '12 mph' into (low, high). Throws on malformed input."""
    nums = re.findall(r"\d+", wind_str or "")
    if not nums:
        raise ValueError(f"Cannot parse wind string: {wind_str!r}")
    if len(nums) == 1:
        v = float(nums[0])
        return (v, v)
    return (float(nums[0]), float(nums[1]))


def sum_precip_inches(observations: list, hours_back: int, now: datetime) -> float:
    cutoff = now - timedelta(hours=hours_back)
    total_mm = 0.0
    for obs in observations:
        props = obs["properties"]
        ts = datetime.fromisoformat(props["timestamp"].replace("Z", "+00:00"))
        if ts < cutoff:
            continue
        mm = (props.get("precipitationLastHour") or {}).get("value")
        if mm is not None:
            total_mm += mm
    return round(total_mm / MM_PER_INCH, 2)


def daylight_remaining_minutes(now: datetime) -> int:
    """Approximate sunset for Wausau lat/lng using simple solar ephemeris.
    
    Good enough for filtering "is there time for this hike" - within a few minutes.
    """
    day_of_year = now.timetuple().tm_yday
    decl_rad = math.radians(23.45 * math.sin(math.radians(360 / 365 * (day_of_year - 81))))
    lat_rad = math.radians(WAUSAU_LAT)
    cos_h = -math.tan(lat_rad) * math.tan(decl_rad)
    if not -1 <= cos_h <= 1:
        return 0
    h_deg = math.degrees(math.acos(cos_h))
    # Solar noon (UTC) at Wausau longitude
    solar_noon_utc_hour = 12 - WAUSAU_LNG / 15
    sunset_utc_hour = solar_noon_utc_hour + h_deg / 15
    midnight_utc = now.replace(hour=0, minute=0, second=0, microsecond=0)
    sunset_utc = midnight_utc + timedelta(hours=sunset_utc_hour)
    remaining = (sunset_utc - now).total_seconds() / 60
    return max(0, int(remaining))


def main() -> None:
    if not NWS_FORECAST.exists():
        raise FileNotFoundError(f"{NWS_FORECAST} missing - run scrapers/nws_forecast.py")
    if not NWS_OBSERVATIONS.exists():
        raise FileNotFoundError(f"{NWS_OBSERVATIONS} missing - run scrapers/nws_observations.py")

    forecast = json.loads(NWS_FORECAST.read_text())
    obs_data = json.loads(NWS_OBSERVATIONS.read_text())
    observations = obs_data["features"]
    now = datetime.now(timezone.utc)

    periods_out = []
    for p in forecast["properties"]["periods"][:4]:
        wind_low, wind_high = parse_wind_mph(p.get("windSpeed"))
        periods_out.append({
            "name": p["name"],
            "start_time": p["startTime"],
            "end_time": p["endTime"],
            "is_daytime": p["isDaytime"],
            "temp_f": p["temperature"],
            "wind_mph_low": wind_low,
            "wind_mph_high": wind_high,
            "precip_chance": (p.get("probabilityOfPrecipitation") or {}).get("value") or 0,
            "short_forecast": p["shortForecast"],
        })

    daytime = next((p for p in periods_out if p["is_daytime"]), periods_out[0])
    precip_24h = sum_precip_inches(observations, 24, now)
    precip_72h = sum_precip_inches(observations, 72, now)

    output = {
        "fetched_at": now.isoformat(),
        "location": {
            "name": "Wausau, WI",
            "lat": WAUSAU_LAT,
            "lng": WAUSAU_LNG,
            "nws_office": "GRB",
            "nws_grid": [25, 50],
            "observation_station": "KCWA",
        },
        "precipitation": {
            "last_24h_in": precip_24h,
            "last_72h_in": precip_72h,
        },
        "forecast": {
            "periods": periods_out,
        },
        # Pre-shaped for transforms/score.py - one place to change if scoring inputs change.
        "scoring_context": {
            "recent_precip_in_24h": precip_24h,
            "recent_precip_in_72h": precip_72h,
            "forecast_temp_f": daytime["temp_f"],
            "forecast_wind_mph": daytime["wind_mph_high"],
            "forecast_precip_chance": daytime["precip_chance"],
            "daylight_remaining_minutes": daylight_remaining_minutes(now),
            "active_closure_ids": [],
        },
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2))
    print(f"Wrote conditions to {OUTPUT_PATH}")
    print(f"  Precip 24h: {precip_24h}\"")
    print(f"  Precip 72h: {precip_72h}\"")
    print(f"  Today: {daytime['name']} {daytime['temp_f']}F, "
          f"wind {daytime['wind_mph_high']}mph, {daytime['precip_chance']}% precip - "
          f"{daytime['short_forecast']}")
    print(f"  Daylight remaining: {output['scoring_context']['daylight_remaining_minutes']}min")


if __name__ == "__main__":
    main()
