"""Per-trail scoring. Pure functions, no I/O, deterministic.

Inputs:
    trail       — dict from data/processed/trails/, with `editorial` merged in
    conditions  — dict from data/processed/conditions.json
    preferences — user filter dict (may be empty)

Output:
    ScoreResult dict: { trail_id, name, score (0-100), factors, hard_filters_failed }

Each soft factor is its own function returning (value 0-1, note string).
Hard filters short-circuit with reasons; the caller decides how to surface them.
"""

from datetime import datetime

DIFFICULTY_RANK = {"easy": 1, "moderate": 2, "difficult": 3, "strenuous": 4}

# Soft factor weights — must sum to 1.0
WEIGHTS = {
    "mud_risk": 0.25,
    "daylight": 0.15,
    "exposure": 0.20,
    "seasonality": 0.15,
    "scenery_match": 0.15,
    "freshness": 0.10,
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9


# --- Soft factors -----------------------------------------------------------

def mud_score(trail: dict, ctx: dict) -> tuple:
    susc = trail["editorial"]["mud_susceptibility"]
    multiplier = {"low": 0.2, "moderate": 0.5, "high": 1.0}[susc]
    wetness = min(1.0, (ctx["recent_precip_in_72h"] * 0.7 + ctx["recent_precip_in_24h"] * 1.5) / 2)
    penalty = multiplier * wetness
    value = 1 - penalty
    if penalty > 0.5:
        note = f"Likely muddy ({ctx['recent_precip_in_72h']:.1f}\" in 72h)"
    elif penalty > 0.2:
        note = "Some muddy spots possible"
    else:
        note = "Trail should be dry"
    return value, note


def daylight_score(trail: dict, ctx: dict) -> tuple:
    daylight = ctx["daylight_remaining_minutes"]
    miles = trail["attributes"]["length_m"] / 1609.34
    gain_ft = trail["attributes"]["elevation_gain_m"] * 3.281
    # Naismith-adjusted: 30 min/mi flat pace + 30 min per 1000ft of ascent + 20 min buffer.
    # The 30 min/mi pace is conservative for casual hikers; Naismith's original
    # was 20 min/mi for fit hikers. The +30 min/1000ft term is the canonical climbing add.
    est_minutes = miles * 30 + (gain_ft / 1000) * 30 + 20
    if est_minutes <= 0:
        return 1.0, "Trivially short"
    ratio = daylight / est_minutes
    if ratio >= 1.5:
        return 1.0, "Plenty of daylight"
    if ratio >= 1.0:
        return 0.7, "Cutting it close - bring a headlamp"
    return 0.2, f"Not enough daylight (~{int(est_minutes)} min needed)"


def exposure_score(trail: dict, ctx: dict) -> tuple:
    exposure = trail["editorial"]["exposure"]
    wind = ctx["forecast_wind_mph"]
    temp = ctx["forecast_temp_f"]
    if exposure == "sheltered":
        return 1.0, "Sheltered from weather"
    if exposure == "mixed":
        if wind > 25 or temp < 25:
            return 0.7, "Some exposed sections - dress in layers"
        return 0.95, "Mostly comfortable conditions"
    # exposed
    if wind > 25:
        return 0.4, f"Exposed and windy ({wind:.0f} mph)"
    if temp < 25:
        return 0.5, f"Exposed and cold ({temp}F)"
    if temp > 85:
        return 0.5, f"Exposed and hot ({temp}F) - bring water"
    return 0.85, "Open trail, comfortable today"


def seasonality_score(trail: dict, ctx: dict) -> tuple:
    season_tags = set(trail["editorial"].get("seasonality") or [])
    month = datetime.fromisoformat(ctx["fetched_at"].replace("Z", "+00:00")).month
    if month in (9, 10) and "fall_color" in season_tags:
        return 1.0, "Peak fall color season"
    if month in (4, 5, 6) and "wildflower" in season_tags:
        return 1.0, "Wildflower season"
    if month in (12, 1, 2) and ("winter_snowshoe" in season_tags or "winter_xc" in season_tags):
        return 1.0, "Good winter trail"
    return 0.7, "OK time of year"


def scenery_score(trail: dict, prefs: dict) -> tuple:
    preferred = set(prefs.get("prefer_scenery") or [])
    if not preferred:
        return 0.75, "No scenery preference set"
    have = set(trail["editorial"].get("scenery_tags") or [])
    matches = preferred & have
    if not matches:
        return 0.3, "No matching scenery"
    if matches == preferred:
        return 1.0, f"All preferred scenery: {', '.join(sorted(matches))}"
    return 0.7, f"Some preferred scenery: {', '.join(sorted(matches))}"


def freshness_score(trail: dict, ctx: dict) -> tuple:
    last_check = trail["editorial"].get("last_field_check")
    if not last_check:
        return 0.5, "Never field-checked"
    fetched = datetime.fromisoformat(ctx["fetched_at"].replace("Z", "+00:00"))
    check_date = datetime.fromisoformat(str(last_check)).replace(tzinfo=fetched.tzinfo)
    age_days = (fetched - check_date).days
    if age_days < 90:
        return 1.0, "Recently field-checked"
    if age_days < 365:
        return 0.85, f"Verified {age_days} days ago"
    return 0.5, f"Stale verification ({age_days} days)"


# --- Hard filters -----------------------------------------------------------

def hard_filter(trail: dict, ctx: dict, prefs: dict) -> list:
    failed = []
    if not trail.get("editorial"):
        return ["awaiting_field_check"]   # short-circuit; can't apply other filters

    if trail["id"] in set(ctx.get("active_closure_ids") or []):
        failed.append("closure")

    if prefs.get("max_drive_minutes") is not None \
            and trail["derived"]["drive_minutes_from_wausau"] > prefs["max_drive_minutes"]:
        failed.append("drive_time")

    if prefs.get("length_range_m"):
        lo, hi = prefs["length_range_m"]
        if not lo <= trail["attributes"]["length_m"] <= hi:
            failed.append("length")

    if prefs.get("must_allow_dogs") and trail["editorial"].get("dog_policy") == "prohibited":
        failed.append("dogs")

    if prefs.get("must_be_family_friendly") and not trail["editorial"].get("family_friendly"):
        failed.append("family")

    if prefs.get("difficulty_max"):
        # Effective difficulty: editorial.difficulty overrides when present,
        # otherwise fall back to the computed estimate from length + gain.
        eff_diff = trail["editorial"].get("difficulty") \
            or trail["attributes"].get("difficulty_estimated")
        if eff_diff and DIFFICULTY_RANK[eff_diff] > DIFFICULTY_RANK[prefs["difficulty_max"]]:
            failed.append("difficulty")

    return failed


# --- Main entry -------------------------------------------------------------

def score_trail(trail: dict, conditions: dict, preferences: dict) -> dict:
    ctx = dict(conditions["scoring_context"])
    ctx["fetched_at"] = conditions["fetched_at"]

    failed = hard_filter(trail, ctx, preferences)
    if failed:
        return {
            "trail_id": trail["id"],
            "name": trail["name"],
            "score": 0,
            "factors": [],
            "hard_filters_failed": failed,
        }

    factor_fns = [
        ("mud_risk",      lambda: mud_score(trail, ctx)),
        ("daylight",      lambda: daylight_score(trail, ctx)),
        ("exposure",      lambda: exposure_score(trail, ctx)),
        ("seasonality",   lambda: seasonality_score(trail, ctx)),
        ("scenery_match", lambda: scenery_score(trail, preferences)),
        ("freshness",     lambda: freshness_score(trail, ctx)),
    ]

    factors = []
    weighted_sum = 0.0
    for name, fn in factor_fns:
        value, note = fn()
        weight = WEIGHTS[name]
        factors.append({"name": name, "value": round(value, 3), "weight": weight, "note": note})
        weighted_sum += value * weight

    return {
        "trail_id": trail["id"],
        "name": trail["name"],
        "score": round(100 * weighted_sum, 1),
        "factors": factors,
        "hard_filters_failed": [],
    }
