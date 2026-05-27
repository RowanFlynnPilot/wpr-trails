---
description: Scaffold a new trail data source with the project's standard pattern
argument-hint: <source-name> (e.g. dnr-county-forest, marathon-parks)
---

Add a new trail data source called $ARGUMENTS following the project's
established pattern. This is a multi-file change.

## Pattern to follow

1. **New scraper file**: `scrapers/<source>.py`
   - Network-bound, outputs raw JSON to `data/raw/<source>.json`
   - Use the requests library, set User-Agent to `wpr-trails/0.1 (https://github.com/RowanFlynnPilot/wpr-trails)`
   - Filter to the 6-county bbox: (44.25, -91.00, 45.75, -88.15) [south, west, north, east]
   - Throw on empty results, don't silently succeed with no data
   - Single `fetch()` function for testability + `main()` for CLI use
   - Reference existing scrapers (`scrapers/dnr_ice_age.py` is the closest template
     for a DNR ArcGIS source; `scrapers/osm_trails.py` for an OSM source)

2. **Builder function in `transforms/build_trails.py`**:
   - New function `build_from_<source>(data)` that yields trail dicts
   - Follow the schema layers exactly: id, name, activities, sources, geometry,
     attributes, editorial (empty `{}`), derived
   - Use `slugify()` and the `id` prefix pattern (`state-`, `iat-`, `osm-` etc.)
   - Compute length from geometry using `length_m()`, don't trust source-provided length
   - Set `attributes.counties` via `counties_for(geometry)`
   - Set `derived.centroid`, `derived.bbox`, `derived.drive_minutes_from_wausau`

3. **OSM dedup consideration**: If this source duplicates trails already in
   the OSM hiking-route layer, extend `is_osm_duplicate()` in build_trails.py
   to filter them out.

4. **Update the pipeline entry points**:
   - Add the scraper to `.github/workflows/weekly-pipeline.yml` after the other scrapers
   - Add to the `/run-pipeline` command (`.claude/commands/run-pipeline.md`)
   - Update the data sources table in `README.md`

5. **Test end-to-end**:
   - Run the new scraper alone, verify `data/raw/<source>.json` exists
   - Run `python -m transforms.build_trails` and confirm new trails appear in
     `data/processed/index.json`
   - Spot-check one new trail's JSON file for correct schema

## Important principles

- Surgical changes only. Don't refactor existing code; add alongside.
- One scraper per source - no fallback paths or multiple endpoints.
- Throw fast on missing/bad data. No silent defaults.
- Don't add fields to the schema without discussing - other code reads by name.

## Ask before starting

What source is this? Need:
- Source URL or API endpoint
- Whether it provides activity codes (hiking/snowshoe/etc.) or needs to default
- Whether it duplicates anything in OSM or other DNR layers
