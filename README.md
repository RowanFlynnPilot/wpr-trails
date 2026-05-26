# wpr-trails

Hiking trail conditions and planning tool for Wausau Pilot & Review, covering
Marathon County and its five contiguous neighbors (Lincoln, Langlade, Taylor,
Shawano, Portage).

Summer mode: full planning for hiking — trail geometry, attribute filters,
conditions-aware "best trail today" scoring.

Winter mode (planned): conditions/status for snowshoe and snowmobile, no
routing (per county clubs' guidance against third-party trail routing).

## Status

**Build-side feature-complete; frontend pending.** The pipeline produces:
- 74 trails across the 6-county area
- Per-trail elevation profile, computed difficulty, geometry
- Auto-derived editorial drafts (scenery, parking, exposure, dog policy)
  with provenance, plus human-curated overrides
- Hourly weather conditions and ranked recommendations

The frontend (Vite/React/Leaflet) is the next milestone.

## Architecture

```
scrapers/        Network-bound pulls; one source per file
transforms/      Pure transforms on local data; build the schema
data/raw/        Raw scraper output, cached
data/processed/  Schema-shaped output for the frontend to consume
data/editorial.yaml  Human-curated per-trail metadata (difficulty, mud, etc.)
```

Two cron tiers:

**Weekly** — slow-changing data
```
python -m scrapers.county_boundaries     # one-time
python -m scrapers.osm_trails
python -m scrapers.dnr_ice_age
python -m scrapers.dnr_state_trails
python -m scrapers.osm_landcover              # ~1 min, 6500+ forest polygons
python -m transforms.build_trails
python -m transforms.enrich_elevation         # ~3 min, samples 10K+ points
python -m transforms.enrich_editorial_auto    # ~10 min, OSM features per trail
```

**Hourly** — fast-changing data + scoring
```
python -m scrapers.nws_forecast
python -m scrapers.nws_observations
python -m scrapers.nws_alerts
python -m transforms.build_conditions
python -m transforms.build_scores
```

## Data sources

| Source | Purpose | Update cadence |
|--------|---------|----------------|
| Census TIGERweb | 6-county polygon boundaries | One-time |
| OpenStreetMap (Overpass API) | Named hiking-route relations | Weekly |
| WI DNR ArcGIS REST (Ice Age Trail layer) | Authoritative IAT segments | Weekly |
| WI DNR ArcGIS REST (State Trail layer) | State recreational trails + activity codes | Weekly |
| Open Topo Data (USGS 3DEP NED10m) | Per-point elevation for profile + gain | Weekly |
| NWS API (forecast + observations) | Forecast, recent precip from KCWA | Hourly |
| NWS API (alerts) | Active warnings / closure triggers | Hourly |

## Schema

Trail records use five separated layers:
- `sources` — provenance per source
- `geometry` — single GeoJSON LineString or MultiLineString
- `attributes` — factual fields (length, surface, blaze, counties)
- `editorial` — human-curated (difficulty, mud, exposure, scenery tags)
- `derived` — computed at build (centroid, bbox, drive time)

The scoring algorithm is a transparent weighted sum of six factors with
hard-filter short-circuits. Each factor returns a `(value, note)` tuple so the
UI can explain *why* a trail ranks where it does. See `transforms/score.py`.

**Computed difficulty.** Every trail gets an `attributes.difficulty_estimated`
field derived from length + elevation gain (formula: `sqrt(miles)*2 + gain_ft/500`,
binned into easy/moderate/difficult/strenuous). When `editorial.difficulty` is
present, it overrides the computed estimate — editorial captures terrain nuance
(rocky, technical, well-graded) that mechanical length+gain cannot.

**Daylight estimation.** Uses Naismith's rule: 30 min/mile flat pace + 30 min
per 1000ft of cumulative ascent + 20 min buffer. This correctly distinguishes
a short-steep trail from a long-flat trail of similar mileage.

## Editorial layer: two-file cascade

Trail "feel" attributes (mud susceptibility, exposure, scenery, parking,
dog policy, family-friendliness, seasonality) live in two YAML files:

- **`data/editorial_auto.yaml`** — machine-generated drafts for every trail.
  Built by `transforms/enrich_editorial_auto.py`, which combines:
  - OSM nearby features along trail geometry (scenery, parking)
  - OSM forest/wood polygon coverage (exposure)
  - Elevation profile (high-elevation exposure check)
  - Managing authority (dog policy default)
  - Trail attributes (family-friendly from difficulty + length)

  Each value carries a `_provenance` block showing where it came from. The
  `validated: false` flag indicates the entry hasn't been human-reviewed.

- **`data/editorial.yaml`** — human-curated overrides. Wins per-field at
  score time. Add an entry here when you want to correct an auto value.

**Known limitations of auto-enrichment** (all overrideable in editorial.yaml):
- OSM forest data is incomplete in central WI; some national/state forests
  aren't tagged. Conservative default is "sheltered" when uncertain.
- Whole-park forest polygons (e.g. Rib Mtn State Park) can't distinguish
  canopy variation, so trails crossing exposed ridges within a "forest"
  polygon get tagged sheltered. Editorial overrides for ridgeline trails.
- `mud_susceptibility` and `drainage` currently default to "moderate" / "loamy"
  pending USDA SSURGO soil data integration (Phase 2).

## Local setup

```
pip install -r requirements.txt
python -m scrapers.county_boundaries
# run the rest of the cron-tier-1 commands once
# run the cron-tier-2 commands once
```

Outputs land in `data/processed/`:
- `trails/{id}.json` — per-trail records, one file each
- `index.json` — lightweight list for the map view
- `conditions.json` — current weather + scoring context
- `scores.json` — ranked trails for today, plus filtered-out reasons

## Data attribution

Trail and basemap data:
- **OpenStreetMap contributors** — hiking routes and landcover polygons,
  via Overpass API. Data made available under
  [ODbL](https://opendatacommons.org/licenses/odbl/). Any frontend or
  published output of this project must credit OpenStreetMap visibly.
- **Wisconsin DNR** — Ice Age Trail and State Trail GIS, via public
  ArcGIS REST services.
- **U.S. Geological Survey 3DEP** — 10m DEM elevation data, sampled via
  [Open Topo Data](https://www.opentopodata.org/). Public domain.
- **NOAA / National Weather Service** — forecast, observations, alerts.
  Public domain.
- **U.S. Census Bureau TIGERweb** — county boundary polygons. Public domain.

This project is a derivative work of OpenStreetMap. Modifications to OSM data
should be contributed back upstream when feasible.

## License

MIT — see [LICENSE](LICENSE).
