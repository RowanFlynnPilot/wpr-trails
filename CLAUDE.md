# CLAUDE.md

Project context for AI assistants. Read this before making changes.

## What this is

A hiking trail conditions and planning tool for Wausau Pilot & Review, a
nonprofit local news outlet covering central Wisconsin. Covers Marathon
County and its five contiguous neighbors: Lincoln, Langlade, Taylor,
Shawano, Portage. Hiking-focused for summer; snowshoe/snowmobile/XC mode
is planned (currently scaffolded but conditions-only, not planning).

## Architecture (one-screen mental model)

```
Network sources             Local pipeline           Frontend (planned)
────────────────────       ──────────────────       ────────────────────
OSM Overpass        ─┐                          ┌─ trails.{wpr}.com
WI DNR ArcGIS REST  ─┤    scrapers/    →        │  (Vite/React/Leaflet)
USGS 3DEP elevation ─┼─→  (Python)              │
NWS API             ─┤              ↓           │  Consumes static JSON
Census TIGER        ─┘    transforms/  →        │  via GitHub Pages
                          (Python)              │
                                ↓               │
                          data/processed/  ─────┘
                          (JSON)
```

Two cron tiers:
- **Weekly**: trail geometry, elevation enrichment, editorial auto-derivation
- **Hourly**: weather conditions, alerts, score rebuild

## Key design choices

1. **Editorial cascade** (`data/editorial.yaml` overrides `data/editorial_auto.yaml`,
   per-field). The auto file is machine-derived from OSM + elevation + managing
   authority. The non-auto file is human-curated nuance. Never overwrite human
   edits with auto values.

2. **Single source of truth per field**. No silent defaults. If a scoring input
   is missing, the algorithm filters the trail out with a clear reason. The
   `_provenance` block in editorial_auto entries shows where each value came
   from, so spot-checks are possible.

3. **Schema layers** in trail records (see `data/processed/trails/*.json`):
   - `sources` — per-source provenance with last_fetched
   - `geometry` — single GeoJSON LineString or MultiLineString
   - `attributes` — factual fields (length, surface, blaze, counties, elevation)
   - `editorial` — populated at score time from the cascade
   - `derived` — computed at build (centroid, bbox, drive time)

4. **OSM ↔ DNR deduplication**. State Trails and IAT segments appear in both
   OSM (as `route=hiking` relations) and DNR (as authoritative geometry).
   `build_trails.py` drops OSM duplicates by name match; keeps connector
   relations since DNR doesn't track between-segment gaps.

5. **Scoring is transparent**. `transforms/score.py` is a pure function returning
   six factors, each with a `(value, note)` tuple. The UI is intended to
   surface the top contributing factors so users see *why* a trail ranks
   where it does, not just a score.

## Pipeline command order

Weekly (slow data):
```
python -m scrapers.county_boundaries     # one-time
python -m scrapers.osm_trails
python -m scrapers.dnr_ice_age
python -m scrapers.dnr_state_trails
python -m scrapers.osm_landcover
python -m transforms.build_trails
python -m transforms.enrich_elevation
python -m scrapers.usda_ssurgo           # depends on built trails
python -m transforms.enrich_editorial_auto
```

Hourly (fast data):
```
python -m scrapers.nws_forecast
python -m scrapers.nws_observations
python -m scrapers.nws_alerts
python -m transforms.build_conditions
python -m transforms.build_scores
```

## Known limitations (Phase 2 work)

1. **Exposure is approximate**. OSM forest polygons are coarse-grained (whole
   parks), so trails crossing exposed ridges *within* a tagged forest get
   flagged sheltered. Editorial overrides for the trails that matter.

2. **Frontend is scaffolded, not feature-complete**. `web/` has the map view
   with filter chips and a per-trail detail panel; deployed to GitHub Pages.
   Missing: scenery-preference filters, drive-time slider, weather banner,
   mobile layout polish.

3. **Snowmobile is conditions-only**. Winter mode (planned) per central WI
   snowmobile clubs' explicit guidance against third-party routing.

## Conventions

- Surgical changes over rewrites. If a function does the right thing for 90%
  of cases, don't refactor — patch the 10%.
- One way to do things. No fallback paths; if preconditions aren't met,
  throw with a clear error.
- Factor functions in `score.py` are single-responsibility, return
  `(value: float, note: str)`, never raise on present-but-degraded data.
- All YAML files are human-edit-friendly. Comments allowed. Field order
  matters for readability.

## What NOT to change without discussing first

- The schema layers in trail records (sources/geometry/attributes/editorial/derived).
  Other code reads these by name; changes propagate widely.
- The cascade order (editorial.yaml > editorial_auto.yaml). User trust depends
  on human edits never being silently overwritten.
- The scoring weight totals (must sum to 1.0). Changes affect all rankings.

## File-level pointers

- `scrapers/`: one file per external source. Outputs to `data/raw/`. No
  cross-dependencies between scrapers.
- `transforms/`: read from `data/raw/`, write to `data/processed/`. May
  depend on each other (see import statements).
- `transforms/build_index.py`: factored helper called by both `build_trails`
  and `enrich_elevation` to keep `data/processed/index.json` in sync.
- `transforms/forest_coverage.py`: spatial index module, not a transform proper.
  Loaded once per `enrich_editorial_auto` run.

## When extending

- Adding a new external source → new file in `scrapers/`. Output to
  `data/raw/<source>.json`. Update README data sources table.
- Adding a new factor to scoring → add function in `score.py`, update
  `WEIGHTS` dict (rebalance to sum to 1.0), add to `factor_fns` list in
  `score_trail()`.
- Adding a new editorial field → add to `editorial_auto.yaml` schema (in
  `enrich_editorial_auto.py`) AND to the seed `editorial.yaml`. Update
  any scoring functions that consume it.
