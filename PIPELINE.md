# Trail Data Pipeline — START HERE

**This is the one file to re-read when you come back to the project.**
It explains how trail data gets created, quality-checked, tested locally, and
shipped. Everything runs locally; **deployment is manual** (you copy tested
files to the web host yourself).

---

## The mental model (30 seconds)

```
  pipeline.config.json        ← you edit this (the state list + flags)
          │
          ▼
  scripts/run-pipeline.py     ← one command, reads the config
          │
          ├─ 1. generate GPS     (optional) real .gpx preferred → synthetic fallback (flagged)
          ├─ 2. generate nearby  link nearest in-state peaks for hikes with none
          ├─ 3. generate desc    factual paragraph per trail (fills empty only)
          ├─ 4. generate SEO     fills missing meta/canonical/schema from real fields
          ├─ 5. check links      nearby_peaks internal links resolve (retention + SEO)
          ├─ 6. audit quality     scripts/audit-gps-quality.py
          └─ 7. validate           scripts/validate-trail-data.js
          │
          ▼
  pipeline-reports/<state>.json   ← what passed / what needs work
          │
          ▼
  test locally (cd website && npm run dev)
          │
          ▼
  MANUALLY upload changed website/src/data/<state>/ files to web host
```

Trail data lives in `website/src/data/<state>/<slug>.json`. Each file's
`trails[0].geo` holds the GPS `path` + elevation `chart` that the frontend
renders (map + elevation profile).

---

## Daily workflow

### A. Re-run quality checks on everything
```bash
python3 scripts/run-pipeline.py
```
Audits every enabled state and runs validation. Read the SUMMARY at the bottom
and the per-state files in `pipeline-reports/`.

### Enabling a state (one at a time)
`pipeline.config.json` lists **all 50 US states, all `enabled: false`**. To start
working a state:
1. Set its `"enabled": true` (and update its `data_sources` if it still shows the
   "UPDATE before enabling" placeholder).
2. Create the trail files — two ways:

   **a) Bulk import from OpenStreetMap (whole state at once):**
   ```bash
   python3 scripts/import-state.py <state> --min-ele 3000   # try --dry-run first
   ```
   One-command bootstrap — import, enable the state in config, and run the
   pipeline in a single step:
   ```bash
   python3 scripts/import-state.py <state> --min-ele 3000 --enable --pipeline
   ```
   Queries the Overpass API for every named peak in the state and writes one
   trail JSON each, pre-filled with the **real, verifiable** facts OSM has
   (name, coordinates, elevation) plus ODbL attribution. It does **not** invent
   distance, difficulty or route geometry — those stay blank, and each file is
   marked `imported-unverified` so the validator keeps it flagged until a human
   confirms it. OSM returns *everything* (a state can have 1000+ named bumps),
   so filter with `--min-ele` / `--min-prominence` / `--limit` to keep only real
   hiking destinations. Always `--dry-run` first to see the count.

   **b) Scaffold a single trail by hand:**
   ```bash
   python3 scripts/new-trail.py <state> <trail-slug> --name "Display Name"
   ```
   Same schema, all facts blank for you to fill.

   **Curate after a bulk import** (OSM returns lots of noise — minor hills with
   no prominence or Wikidata entry). Rank and prune to the real destinations:
   ```bash
   python3 scripts/curate-state.py <state>                 # report only
   python3 scripts/curate-state.py <state> --keep-top 15 --apply
   ```
   `--apply` MOVES the low-signal files to `website/src/data/_rejected/<state>/`
   (reversible, gitignored — never deleted) so you enrich only the keepers.
   Hand-curated files (no `osm` block) are never touched. Publishing dozens of
   thin, near-duplicate peak pages hurts SEO, so curate before you enrich.

   Either way, finish each trail by adding route distance/difficulty and a real
   GPX (`gpx-downloads/<slug>.gpx` → `gpx-to-geo.py`), verifying against the
   official land manager, then removing the `_status` key.
3. Run `python3 scripts/run-pipeline.py --state <slug>` — it auto-generates SEO
   and nearby_peaks, then audits GPS and validates.

States with no data folder yet are skipped safely by every tool, so a default
run only touches the states you've enabled and populated.

### B. Work on just one state
1. Open `pipeline.config.json`, find the state, set `"rerun": true`.
2. Run:
   ```bash
   python3 scripts/run-pipeline.py --rerun
   ```
   (or skip the config edit: `python3 scripts/run-pipeline.py --state maine`)
3. Fix the trails listed under "needs work", re-run until the state shows `PASS`.
4. Set `"rerun": false` again when done.

### C. Test in the browser before shipping
```bash
cd website
npm run dev          # http://localhost:4321
# open the state page and a couple of trail pages, confirm map + chart look right
```

### D. Ship (manual)
Copy only the changed `website/src/data/<state>/*.json` files to the web host.
The pipeline never uploads anything.

---

## How GPS data is created (accurate first, synthetic as fallback)

For a trail whose `trails[0].geo.path` is missing, `run-pipeline.py` (when the
state has `"generate_gps": true`) does this **per trail**:

1. **Real GPX (accurate & reliable)** — if `gpx-downloads/<slug>.gpx` exists, it
   runs `scripts/gpx-to-geo.py` to extract the true track + elevation. This is
   the preferred, trustworthy source. Validate a GPX first with
   `python3 scripts/validate-gpx.py gpx-downloads/<slug>.gpx`.
2. **Synthetic fallback (flagged)** — if no GPX and the state has
   `"synthetic_fallback": true`, it runs `scripts/enhance-gps-path.py` to
   interpolate a path so the page still renders. These trails are **listed in
   the report under `synthetic_gps`** so you know to upgrade them with a real
   GPX later. The audit also flags them ("Path very straight… oversimplified").

> To get accurate data for a trail: download a GPX from a trusted source
> (CalTopo, Gaia GPS, a verified track), drop it in `gpx-downloads/<slug>.gpx`,
> and re-run with `generate_gps: true`. The real track replaces the synthetic one.

**Real GPX is applied automatically.** On every run the pipeline scans
`gpx-downloads/<slug>.gpx` and converts any match into that trail's route
(path + distance + gain) — so finishing a trail is just "drop the GPX, re-run".
This is always on and independent of `generate_gps`. The `generate_gps` flag
only controls the *synthetic* fallback (an interpolated, flagged path for
trails with no GPX), which stays `false` by default. The trail still needs its
`_status` flag removed to publish — that's the human verification step.

---

## How SEO data is created

When a state has `"generate_seo": true` (default), the pipeline runs
`scripts/generate-seo.py` on every trail missing SEO and fills in:

- `meta_title`, `meta_description` — search-friendly, derived from the trail's
  real name / state / elevation / route stats
- `canonical_url` — `/trails/<state>/<slug>`
- `schema_place` — Place + GeoCoordinates + per-trail HikingTrail entries
- `schema_faq` — FAQPage with 5 Q&As built from the trail's own stats

It is **idempotent**: existing SEO is preserved; only missing pieces are added.
Use `python3 scripts/generate-seo.py --force <file>` to rebuild a single file.

> These values render through `src/layouts/Layout.astro`, which forwards the
> `mountain` prop to `SEOHead` and exposes a `<slot name="head" />` for extra
> per-page schema (e.g. `TrailSchema`, `near/` and `challenges/` FAQ schema).
> Before this wiring, trail pages silently shipped a generic meta description
> and dropped their structured data — if you add new page-level schema, inject
> it via `slot="head"`.

---

## Publish gate — drafts never reach visitors

The site only publishes **route-complete** trails. A trail is shown publicly
(generates a page, appears in state listings and the homepage, enters the
sitemap) only when it has a real GPS path **and** a distance, **and** its
`_status` draft flag has been removed. The gate lives in
`website/src/lib/publishReady.js` and is applied in the homepage, state index,
trail detail `getStaticPaths`, and the sitemap.

This is deliberate: a freshly imported OpenStreetMap stub has no route, so
showing it would be a blank, untrustworthy page (the AllTrails comparison —
they never show a routeless trail). Stubs stay invisible until finished. Track
what's left with:
```bash
python3 scripts/draft-status.py [state]   # LIVE vs DRAFT + the exact missing fields
```
To take a draft live: add its route (distance, gain, difficulty + a real GPX via
`gpx-to-geo.py`), verify the facts, and delete the `_status` key. It then
publishes automatically on the next build.

## What "quality" means here

Set in `pipeline.config.json` under `quality`; enforced by
`scripts/audit-gps-quality.py`:

| Signal | Good | Why it matters |
|---|---|---|
| GPS points per mile | ≥ 15 | Sparse paths render as jagged/inaccurate routes |
| Elevation on every point | required | No elevation = no elevation chart |
| Path straightness | < 0.9 | Near-straight paths mean the route was oversimplified |
| Chart points | ≥ 5 (10+ ideal) | Drives the elevation profile graph |
| `data_sources` block | required | Authenticity/safety — see `DATA_QUALITY_SYSTEM.md` |
| `nearby_peaks` links | must resolve | Broken internal links 404 → lost retention + SEO crawl paths |

**Nearby-peaks generation** (`scripts/generate-nearby-peaks.py`, step 2) fills
`nearby_peaks` for any hike that has none, by finding the closest OTHER trails
in the same state via real great-circle distance (within 75 mi, up to 4 links).
Idempotent — existing links are kept. Trails with no peers in range (e.g.
geographically isolated ones) are left unlinked rather than given misleading
distant links. Run standalone: `python3 scripts/generate-nearby-peaks.py [state ...]`.

**Link integrity** (`scripts/check-links.py`) is a hard gate: every
`nearby_peaks` entry must point to a real trail file
(`website/src/data/<state_slug>/<slug>.json`), or the state is marked NEEDS
WORK. Hikes with *no* `nearby_peaks` are reported as a warning (weak internal
linking) — good candidates for enrichment, but not a failure. Run standalone
with `python3 scripts/check-links.py [state ...]`.

A trail scores 0–100; the pipeline marks a state `PASS` only when every trail
is ≥ `quality.min_score` (default 80).

**Every route is audited, not just the first.** A hike can offer several routes
(`trails[]`); since a hiker may pick any of them, the hike's score is gated by
its **weakest** route. The audit reports a per-route breakdown and the pipeline
names the weakest route on each failing line (e.g.
`✗ Mount Pierce … weakest route: 'Webster-Jackson Trail to Pierce'`), so a
strong primary route can no longer mask a poor alternate.

`scripts/validate-trail-data.js` is the second gate: it checks required fields,
GPS/elevation ranges, distance sanity, and `data_sources` freshness across the
whole repo.

---

## pipeline.config.json fields

| Field | Meaning |
|---|---|
| `data_dir` | Where trail JSON lives (`website/src/data`) |
| `gpx_dir` | Where real GPX tracks go (`gpx-downloads/<slug>.gpx`) |
| `report_dir` | Where per-state reports are written (gitignored) |
| `quality.min_score` | Pass threshold per trail (default 80) |
| `states[].enabled` | Include this state in default runs |
| `states[].rerun` | Picked up by `--rerun` (your "do this one now" flag) |
| `states[].generate_gps` | Build missing GPS paths for this state |
| `states[].synthetic_fallback` | Allow interpolated paths when no GPX exists |
| `states[].data_sources` | Default attribution for the state |

---

## Reference docs (deeper dives, not needed day-to-day)

- `DATA_QUALITY_SYSTEM.md` — data sources, attribution format, verification rules
- `CALIFORNIA_TRAIL_ADDITION_GUIDE.md` — how to research & add a new trail
- `GPS_FIX_PRIORITY.md` / `QUICK_START_GPS_FIX.md` — GPS fix background

## Scripts at a glance

| Script | Run when |
|---|---|
| `scripts/run-pipeline.py` | **Always start here** — orchestrates the rest |
| `scripts/import-state.py` | Bulk-import a state's named peaks from OpenStreetMap |
| `scripts/curate-state.py` | Rank imported peaks by notability; prune noise to _rejected/ |
| `scripts/new-trail.py` | Scaffold a single new trail JSON stub (facts blank to fill) |
| `scripts/generate-nearby-peaks.py` | Link nearest in-state peaks for hikes with none |
| `scripts/check-links.py` | Verify nearby_peaks internal links resolve |
| `scripts/generate-description.py` | Write a unique factual paragraph per trail (fills empty only) |
| `scripts/generate-seo.py` | Build meta/canonical/schema from real fields |
| `scripts/check-elevation.py` | Report-only: flag elevations that diverge from USGS (never edits) |
| `scripts/gpx-to-geo.py` | Convert a real GPX into a trail's `geo` (accurate) |
| `scripts/enhance-gps-path.py` | Interpolate a synthetic path (fallback) |
| `scripts/validate-gpx.py` | Sanity-check a GPX before converting |
| `scripts/audit-gps-quality.py` | GPS quality audit (called by the orchestrator) |
| `scripts/validate-trail-data.js` | Field/schema validation (called by the orchestrator) |
