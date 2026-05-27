---
description: Run the weekly or hourly data pipeline locally
argument-hint: weekly | hourly
---

Run the wpr-trails data pipeline for the tier specified in $ARGUMENTS.

## Weekly pipeline (slow data - trails, geometry, editorial auto-derivation)

If $ARGUMENTS is "weekly" or empty, run in order:

```
python -m scrapers.county_boundaries
python -m scrapers.osm_trails
python -m scrapers.dnr_ice_age
python -m scrapers.dnr_state_trails
python -m scrapers.osm_landcover
python -m transforms.build_trails
python -m transforms.enrich_elevation
python -m transforms.enrich_editorial_auto
```

Expected duration: ~15 minutes total. `enrich_editorial_auto` is the long step
(~10 min) because of Overpass rate limits. It's resumable - if interrupted,
re-running picks up where it left off.

## Hourly pipeline (fast data - conditions and scoring)

If $ARGUMENTS is "hourly", run:

```
python -m scrapers.nws_forecast
python -m scrapers.nws_observations
python -m scrapers.nws_alerts
python -m transforms.build_conditions
python -m transforms.build_scores
```

Expected duration: ~30 seconds. Requires the weekly pipeline to have run at
least once (needs `data/processed/trails/` populated).

## After running

Show me:
- Top 5 ranked trails from `data/processed/scores.json`
- Total trail count and how many are ranked vs filtered
- Any errors or warnings from the runs
