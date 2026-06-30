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
          ├─ 1. generate GPS   (optional) real .gpx preferred → synthetic fallback (flagged)
          ├─ 2. generate SEO   fills missing meta/canonical/schema from real fields
          ├─ 3. audit quality   scripts/audit-gps-quality.py
          └─ 4. validate         scripts/validate-trail-data.js
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

By default `generate_gps` is `false` for every state — the pipeline only
audits and validates existing data until you opt a state in.

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

A trail scores 0–100; the pipeline marks a state `PASS` only when every trail
is ≥ `quality.min_score` (default 80).

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
| `scripts/gpx-to-geo.py` | Convert a real GPX into a trail's `geo` (accurate) |
| `scripts/enhance-gps-path.py` | Interpolate a synthetic path (fallback) |
| `scripts/validate-gpx.py` | Sanity-check a GPX before converting |
| `scripts/audit-gps-quality.py` | GPS quality audit (called by the orchestrator) |
| `scripts/validate-trail-data.js` | Field/schema validation (called by the orchestrator) |
