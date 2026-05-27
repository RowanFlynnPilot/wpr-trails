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

## Session 2026-05-26

What I did:
- Scaffolded the frontend in `web/` — Vite 5 + React 18 + TypeScript +
  Tailwind 3 + Leaflet via react-leaflet.
- First commit scope: map view fetches live `index.json` from GitHub Pages,
  renders 74 trail centroids as pins with name/length/difficulty/drive-time
  popups. Sidebar has activity + county multi-select filter chips.
- Added `.claude/launch.json` so `preview_start name=web` boots the dev
  server in future sessions.
- Verified in a real browser via Claude Preview: 74 markers render, no
  console errors, no failed network requests, typecheck clean.

What I learned that changes how to think about the project:
- `index.json` uses `length_m` (meters) and `centroid: [lon, lat]`
  (GeoJSON convention). Frontend types and pin rendering both need to
  respect this — easy to invert lat/lon by accident.
- Activity enum across the data is: hiking, biking, horseback, xc_ski,
  snowshoe, snowmobile. Counties: marathon, lincoln, langlade, taylor,
  shawano, portage. Hard-coded in `web/src/components/FilterBar.tsx` —
  if scrapers ever emit a new value, the chip won't show until added.

What's actually next now:
- Commit 2: trail detail panel. Click a pin → fetch
  `trails/{id}.json` → show editorial summary, attributes, score
  breakdown from `scores.json`.
- Commit 3: GitHub Pages deployment workflow for the app itself
  (currently only the data pipeline publishes to Pages).
- Then SSURGO soil integration (Path B) can land in parallel since
  it's pure data-side work.

### Later same session: commits 2 + 3 landed

Commit 2 (b72b2b4): trail detail panel. Pin click opens a 384px
right-anchored slide-out showing trail name, today's score, factual
attributes (length, elevation gain, difficulty, loop, drive time,
managing authority, blaze, surface, counties), and the six factor
scores with inline bars + notes from scores.json. Added Trail,
Scores, ScoreFactor types; fetchScores + fetchTrail data helpers
with module-level cache for per-trail responses; useScores + useTrail
hooks. Replaced popup with `eventHandlers.click` + selected-icon
hue-rotate variant.

Commit 3 (df53fa9): GitHub Pages deploy workflow. Builds the Vite
app on every push to main, bundles `data/processed/` into the
artifact, deploys via `actions/deploy-pages`. Vite `base` set to
`/wpr-trails/`. Data fetches still use the absolute Pages URL so
local `npm run dev` works without a local data copy.

**REQUIRED MANUAL STEP**: in repo Settings → Pages, switch source
from "Deploy from a branch" to "GitHub Actions". Until that flips,
the deploy workflow runs but the live site stays branch-served.

What I learned during commits 2+3:
- `editorial: {}` is empty in every per-trail JSON. The cascade
  (editorial.yaml + editorial_auto.yaml) is merged Python-side only
  at score time. So the frontend can't surface editorial fields
  directly — it leans on the factor `note` strings in scores.json
  ("Trail should be dry", "Sheltered from weather") which encode the
  editorial nuance indirectly. If we want a richer detail panel
  later, the cleanest fix is a new transform that publishes
  `data/processed/editorial_merged.json`.
- `Difficulty` enum is `easy | moderate | strenuous` (not "difficult"
  — that was a guess in commit 1, fixed in commit 2).
- Claude Preview's headless browser runs at 0×0 viewport, which
  prevents Leaflet from registering visible markers or delivering
  clicks. Pin-click → panel verified by code inspection only;
  human verification needed in real `npm run dev`.

What's actually next now:
- Push these three commits (86a13d8..df53fa9) to origin/main.
- Flip Pages source to "GitHub Actions" in repo settings.
- Wait for first deploy to confirm site is live at
  `https://rowanflynnpilot.github.io/wpr-trails/`.
- Then SSURGO soil integration (Path B) is the highest-leverage
  next chunk of work. Independent from the frontend.

### Same session: SSURGO soil integration shipped

Path B is done. Real `mud_susceptibility` for all 74 trails replaces
the hardcoded "moderate" default; trail score spread went from "all
tied at 91.3" to 12 distinct scores (range 74.8–91.3 on a dry day,
spreads further after rain).

Architecture chose against bulk-downloading SSURGO polygons (~100k
across 6 counties, too large) in favor of per-trail line-intersect
queries via SDA's `SDA_Get_Mukey_from_intersection_with_WktWgs84`
stored procedure. Each trail query takes ~0.4s + 1s polite delay
→ 118s for all 74 trails. Plus one bulk drainage-class lookup for
the 475 unique mukeys. Output cached in `data/raw/ssurgo.json`.

- New `scrapers/usda_ssurgo.py` (queries SDA, writes ssurgo.json)
- `transforms/enrich_editorial_auto.py` now consumes ssurgo.json and
  derives `mud_susceptibility` via a 30%-poorly-drained threshold,
  `drainage` texture via modal hydrologic group first-letter
- `.github/workflows/weekly-pipeline.yml` runs SSURGO between
  enrich_elevation and enrich_editorial_auto
- README + CLAUDE.md updated to remove "Phase 2 soil" note

Validation under simulated 0.8" rain in 72h:
- Yellow Trail (granite ridge, low mud): 0.94 mud_score
- Alta Junction (IAT wetland segment, high mud): 0.72 mud_score
- Same conditions, different soil → different ranking. The whole
  point of the feature.

What I learned that changes how to think about the project:
- SDA's spatial intersect queries against bbox/polygon WKTs time
  out on anything non-trivial (60s+ for a small test polygon). The
  per-WKT stored procedures (`SDA_Get_Mukey_from_intersection_...`)
  are pre-optimized and fast (~0.4s per trail line). Use those.
- SSURGO mupolygon counts in central WI are huge — Marathon County
  alone has 23,501 polygons. Don't bulk-download.
- Hydrologic group dual classifications (A/D, B/D, C/D) signal
  wetland soils: sandy/loamy when drained, clay-like when wet. The
  first letter captures normal-conditions texture; the drainage
  class captures wet-state behavior. Two separate fields, both
  derived from SSURGO, neither redundant.

What's actually next now:
- Push SSURGO commit, watch the deploy land
- The next hourly cron will rebuild scores against the updated
  editorial_auto.yaml, so the live site will reflect real soil-based
  rankings within ~1 hour
- Frontend follow-ups (scenery filter, drive-time slider, weather
  banner) are the next high-leverage UI work
- Trailhead coordinates remain null everywhere — picking the closest
  amenity=parking and snapping to the trail endpoint is the natural
  next data-side enhancement

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
