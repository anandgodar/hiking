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

### Step 3 — Curate (drop the OSM noise, keep real destinations)
```bash
python3 scripts/curate-state.py <state>                  # report only
python3 scripts/curate-state.py <state> --keep-top 15 --apply
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
> (Still run Step 3 curation before shipping.)

### Step 6 — Finish each kept trail (manual, required for publish)
For every JSON in `website/src/data/<state>/`:
- Fill `trails[0].stats`: `distance`, `gain`, `difficulty`, `time`
- Add a real GPS track: drop `gpx-downloads/<slug>.gpx`, then:
  ```bash
  python3 scripts/gpx-to-geo.py gpx-downloads/<slug>.gpx website/src/data/<state>/<slug>.json
  ```
- Verify facts against the official source, then delete the `"_status"` line.
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
| `scripts/curate-state.py` | Rank/prune imported peaks to real destinations |
| `scripts/new-trail.py` | Scaffold one blank trail JSON |
| `scripts/run-pipeline.py` | Orchestrate: nearby → description → SEO → links → audit → validate |
| `scripts/generate-nearby-peaks.py` | Link nearest in-state peaks |
| `scripts/generate-description.py` | Write a factual paragraph per trail |
| `scripts/generate-seo.py` | Build meta/canonical/schema |
| `scripts/check-links.py` | Verify internal links resolve |
| `scripts/check-elevation.py` | Report elevations diverging from USGS (no edits) |
| `scripts/gpx-to-geo.py` | Convert a real GPX into a trail's GPS path |
| `scripts/audit-gps-quality.py` | Score GPS quality (all routes) |
| `scripts/validate-trail-data.js` | Validate required fields / ranges |
