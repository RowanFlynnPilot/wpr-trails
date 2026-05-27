# STATUS.md

Living snapshot for context handoff between sessions. Update at end of each
significant work session. If you're an AI assistant picking this up, read
this AFTER `CLAUDE.md` to see "where things actually are right now."

---

## Current state (as of repo creation)

**Build-side pipeline: feature-complete.** Frontend: not started.

The data pipeline runs end-to-end and produces:
- 74 trails across the 6-county region (5 State Trails, 32 IAT segments, 37 other named hiking routes)
- Per-trail elevation profile, computed difficulty, full geometry
- Auto-derived editorial drafts for all 74 trails (`data/editorial_auto.yaml`)
- Human-curated overrides for 10 well-known trails (`data/editorial.yaml`)
- Hourly conditions and scoring; all 74 trails currently rank

GitHub Actions workflows are deployed and running:
- **Weekly Pipeline** runs Sundays 7am UTC + manual dispatch
- **Hourly Conditions** runs every hour + manual dispatch

Data is publicly fetchable at:
- `https://rowanflynnpilot.github.io/wpr-trails/data/processed/index.json`
- `https://rowanflynnpilot.github.io/wpr-trails/data/processed/scores.json`
- `https://rowanflynnpilot.github.io/wpr-trails/data/processed/trails/{id}.json`

## What's next

Two independent paths. Pick one per session.

### Path A: Frontend scaffold (recommended next)

Build a Vite + React + Leaflet app that consumes the GitHub Pages JSON outputs.
Deploy to a subdomain like `trails.wausaupilotandreview.com`.

Why this first: data is product-ready and showing something on a screen is
huge motivation. Also, real frontend usage will surface what's missing from
the data (trailhead coords, trail descriptions, photos).

Suggested first commit: just the map view loading `index.json` and rendering
trail centroids as pins. Filter by activity + county. Iterate from there.

### Path B: USDA SSURGO soil integration

Replace the default "moderate" / "loamy" values for `mud_susceptibility` and
`drainage` with real soil data from USDA SSURGO. This is the highest-impact
remaining data quality improvement - `mud_risk` has 25% weight in scoring,
but currently every trail scores identically on it.

SSURGO has both SOAP/REST APIs and downloadable GeoTIFFs. New scraper would
be `scrapers/usda_ssurgo.py`, new transform `transforms/forest_coverage.py`
pattern (spatial sampling along trail geometry).

### Smaller improvements

- **Trailhead coordinates**: `derived.trailhead_coords` is currently null
  everywhere. Pick the closest `amenity=parking` from the auto-enrichment data
  and snap to the trail endpoint nearest it.
- **Exposure heuristic**: Currently flags only 1 trail as exposed (Harrison Hills,
  a false positive). The OSM forest-coverage approach is conservative. Editorial
  overrides catch the trails that matter (Yellow, Red, Turkey Vulture).
- **Trail descriptions**: No text fields beyond `editorial.notes`. Could scrape
  WI DNR park pages for state park trails, IATA segment guides for IAT segments.

## Open questions / known limitations

- **7-way tie at score 91.3**: Several short sheltered IAT segments rank
  identically with no user preferences applied. The frontend's filters
  (scenery preference, length range, drive time) will be what differentiates
  them - so this is a "fix it in the UI layer" issue, not a scoring fix.
- **Wisconsin DNR `SURFACE_TYPE` is empty** across our 6-county bbox features.
  Surface tagging relies entirely on OSM data or editorial.
- **OSM activity tags are sparse**. Most non-state trails default to `["hiking"]`
  only, even when locally known to allow biking, horses, or skiing.

## How to add an entry to this file

End of session: append a dated section with what changed.

```
## Session yyyy-mm-dd

What I did:
- ...

What I learned that changes how to think about the project:
- ...

What's actually next now (may differ from the "What's next" section above):
- ...
```
