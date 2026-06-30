# Steps — Running the Trail Data Scripts

A quick, copy-paste cheat sheet. Run all commands from the **repo root**
(`hiking-project/`). For the full explanation of each step, see `PIPELINE.md`.

> One-time on macOS, if you hit a TLS/certificate error fetching data:
> `/Applications/Python\ 3.13/Install\ Certificates.command`  (or `pip3 install --upgrade certifi`)

---

## 0. Get the latest code

```bash
cd /Users/anandgodar/PycharmProjects/hiking-project
git pull origin claude/speckit-installation-86a106
```

---

## 1. Add a new state (the full flow)

### Step 1 — Preview what would import (no files written)
```bash
python3 scripts/import-state.py <state> --min-ele 2000 --dry-run
```
- `<state>` is a slug: `new-jersey`, `colorado`, `new-york`, …
- Tune `--min-ele <feet>` until the count looks reasonable.

### Step 2 — Import the peaks from OpenStreetMap
```bash
python3 scripts/import-state.py <state> --min-ele 2000
```
Writes one JSON per peak to `website/src/data/<state>/`.

### Step 3 — Prune the OSM noise (keep real destinations)
```bash
python3 scripts/curate-state.py <state> prune                   # report only
python3 scripts/curate-state.py <state> prune --keep-top 15 --apply
```
`--apply` moves rejects to `website/src/data/_rejected/<state>/` (reversible).

### Step 4 — Enable the state
Open `pipeline.config.json`, find `<state>`, set `"enabled": true`
(and fill in real `data_sources` if it shows the placeholder).

### Step 5 — Run the pipeline (enrich + audit + validate)
```bash
python3 scripts/run-pipeline.py --state <state>
```
Auto-generates nearby_peaks, descriptions, and SEO; then checks links,
audits GPS, and validates.

> Shortcut for steps 2 + 4 + 5 in one command:
> ```bash
> python3 scripts/import-state.py <state> --min-ele 2000 --enable --pipeline
> ```
> (Still run Step 3 pruning before shipping.)

### Step 5b — Auto-fetch routes, trailheads & features (no manual GPX)
Pull real, public-domain data for every draft, then enrich + publish:
```bash
python3 scripts/fetch-trails.py <state>     # routes from USFS + NPS (name-matched) + elevation
python3 scripts/enrich-poi.py <state>       # trailhead start + parking + along-trail features (OSM)
python3 scripts/run-pipeline.py --state <state>
python3 scripts/curate-state.py <state>     # publishes the ones that pass quality
```
- `fetch-trails.py` tries USFS then NPS, matching a trail by name to the peak
  (e.g. "Mount Rogers" → USFS "Mount Rogers Spur"). Never auto-publishes — the
  quality gate vets each route. Tune coverage with `--radius-km`.
- `enrich-poi.py` sets the **trailhead** as the route start, fills **parking**
  (name + coords + fee), and lists **features** you pass — waterfall, overlook,
  hut, rest area, boulder, cliff, fire tower — each with its mile along the trail.
- For peaks with no public-land route, fall back to a real GPX (below).

### Step 6 — Publish (the quality gate decides)
```bash
python3 scripts/curate-state.py <state>             # auto-publish all that pass quality
python3 scripts/curate-state.py <state> published   # list what's live
python3 scripts/curate-state.py <state> draft       # list drafts + why each is held
```
`curate-state.py <state>` (no sub-command) **auto-publishes every trail that
meets the quality bar** — real GPS route + distance + gain + valid coords +
GPS-audit ≥ `quality.min_score`. Difficulty is computed from distance+gain if
missing. Trails that fail stay **draft** (hidden) with the reason shown. To lift
a draft: drop a real `gpx-downloads/<slug>.gpx`, run the pipeline, then re-run
`curate-state.py <state>`.

> **Drafts are hidden from the site.** A trail only appears publicly once it is
> route-complete (real GPS path + distance, and the `_status` flag removed).
> Freshly imported stubs do **not** generate pages, show on the homepage, or
> enter the sitemap — so a half-empty page can never reach visitors. See what's
> still pending:
> ```bash
> python3 scripts/draft-status.py <state>      # LIVE vs DRAFT, with what each draft needs
> ```
> To **preview drafts locally** (e.g. a state you just imported) without
> publishing them, set `SHOW_DRAFTS=1`:
> ```bash
> cd website && SHOW_DRAFTS=1 npm run dev      # drafts visible locally only
> ```
> A normal `npm run build` (no flag) keeps them hidden in production.

### Step 6 — Finish each kept trail (manual, required for publish)
For every JSON in `website/src/data/<state>/`:
- Fill `trails[0].stats`: `distance`, `gain`, `difficulty`, `time`
- Add a real GPS track: just drop the file at `gpx-downloads/<slug>.gpx`.
  The pipeline **auto-converts any GPX it finds** (path + distance + gain) on
  the next `run-pipeline.py --state <state>` — no manual conversion needed.
  (To convert one immediately by hand: `python3 scripts/gpx-to-geo.py
  gpx-downloads/<slug>.gpx website/src/data/<state>/<slug>.json`.)
- Set difficulty/type/parking and publish in one command (no JSON editing):
  ```bash
  python3 scripts/set-trail.py <state> <slug> \
      --difficulty Moderate --type "Out & Back" --parking "Trailhead name" --publish
  ```
  `--publish` removes the `_status` flag (refused unless the trail has a real
  route). Omit `--publish` to set fields but keep it a draft.
- Re-run the pipeline: `python3 scripts/run-pipeline.py --state <state>`

---

## 2. Add a single trail by hand (instead of importing)

```bash
python3 scripts/new-trail.py <state> <trail-slug> --name "Display Name"
# then fill the blank fields, and run:
python3 scripts/run-pipeline.py --state <state>
```

---

## 3. Routine checks (any time)

```bash
python3 scripts/run-pipeline.py                 # all enabled states
python3 scripts/run-pipeline.py --state <state> # one state
python3 scripts/check-links.py                  # internal links resolve?
python3 scripts/check-elevation.py --state <state> --rounded-only   # report only
node   scripts/validate-trail-data.js           # schema/field validation
python3 scripts/audit-gps-quality.py            # GPS quality scores
```

---

## 4. Test locally

```bash
cd website
npm install        # first time only
npm run dev        # open http://localhost:4321
npm run build      # production build into website/dist/
cd ..
```
Check a state page (`/<state>`) and a trail page (`/<state>/hikes/<slug>`):
map, elevation chart, description, nearby peaks, page title.

---

## 5. Commit your data work

```bash
git add website/src/data/<state> pipeline.config.json
git commit -m "Add <state> trails"
git push origin claude/speckit-installation-86a106
```

---

## 6. Deploy to the web host

The site is a static build — deploy the **built output**, not the source JSON.

```bash
cd website && npm run build
# upload everything inside website/dist/  →  your host's public web root
```
Example with rsync:
```bash
rsync -avz --delete website/dist/ user@yourhost:/path/to/webroot/
```

> Mental model: maintain JSON in `website/src/data/` → `npm run build` →
> ship `website/dist/`.

---

## Script reference

| Script | Purpose |
|---|---|
| `scripts/import-state.py` | Bulk-import a state's peaks from OpenStreetMap |
| `scripts/curate-state.py` | Publish (quality gate decides) · `draft`/`published`/`prune` sub-commands |
| `scripts/new-trail.py` | Scaffold one blank trail JSON |
| `scripts/run-pipeline.py` | Orchestrate: nearby → description → SEO → links → audit → validate |
| `scripts/generate-nearby-peaks.py` | Link nearest in-state peaks |
| `scripts/generate-description.py` | Write a factual paragraph per trail |
| `scripts/generate-seo.py` | Build meta/canonical/schema |
| `scripts/check-links.py` | Verify internal links resolve |
| `scripts/check-elevation.py` | Report elevations diverging from USGS (no edits) |
| `scripts/draft-status.py` | LIVE vs DRAFT trails + exactly what each draft still needs |
| `scripts/fetch-trails.py` | Auto-pull real public-domain routes (USFS + NPS) for drafts |
| `scripts/enrich-poi.py` | Add trailhead start, parking, and along-trail features (OSM) |
| `scripts/enrich-elevation.py` | Fill missing elevation on a 2-D GPS path from Open-Meteo DEM |
| `scripts/set-trail.py` | Set difficulty/type/parking and publish a trail (one command) |
| `scripts/gpx-to-geo.py` | Convert a real GPX into a trail's GPS path |
| `scripts/audit-gps-quality.py` | Score GPS quality (all routes) |
| `scripts/validate-trail-data.js` | Validate required fields / ranges |
