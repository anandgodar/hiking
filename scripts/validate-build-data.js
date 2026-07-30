#!/usr/bin/env node
/**
 * Build gate: FAIL the build on trail-data integrity violations.
 *
 * Runs before `astro build` (see website/package.json). Only PUBLISHED trails
 * can fail the build — drafts are held from the site by design and are
 * reported as warnings so they stay visible without blocking a deploy.
 *
 * Failures (exit 1):
 *   - elevation above 20,310 ft (Denali; nothing in the US exceeds it)
 *   - elevation null, zero or negative
 *   - missing or unusable route geometry
 *   - stored distance disagreeing with the route length implied by its
 *     distance_type by more than 10%
 *
 * The distance check compares against `route_length_mi` (computed from the
 * geometry, see scripts/route_metrics.py) rather than raw geometry length,
 * because an out-and-back's hiked distance is deliberately twice its
 * geometry. Records carrying `distance_source: "authored"` — a curated
 * round-trip figure on incomplete geometry — are reported as warnings, not
 * failures: the number is correct and the route coverage is what is missing,
 * so blocking deploys on them would be wrong.
 */

import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const DATA = join(ROOT, 'website', 'src', 'data');

const US_MAX_ELEVATION_FT = 20310;
const DISTANCE_TOLERANCE = 0.10;
// `distance` is stored to one decimal, so on a sub-mile route rounding alone
// can exceed 10%. Require the absolute gap to be meaningful too, otherwise a
// 0.45 mi loop stored as 0.4 would fail the build for no real defect.
const DISTANCE_TOLERANCE_FLOOR_MI = 0.15;
const SKIP_DIRS = new Set(['_rejected', 'blog', 'guides']);

const failures = [];
const warnings = [];

function walk(dir) {
  const out = [];
  for (const entry of readdirSync(dir)) {
    const p = join(dir, entry);
    if (statSync(p).isDirectory()) {
      if (!SKIP_DIRS.has(entry)) out.push(...walk(p));
    } else if (entry.endsWith('.json')) {
      out.push(p);
    }
  }
  return out;
}

function rel(p) {
  return p.replace(ROOT + '/', '');
}

let checked = 0;
for (const file of walk(DATA)) {
  let record;
  try {
    record = JSON.parse(readFileSync(file, 'utf8'));
  } catch (err) {
    failures.push(`${rel(file)}: unparseable JSON — ${err.message}`);
    continue;
  }
  if (!record || typeof record !== 'object' || !record.state_slug) continue;

  const isDraft = Boolean(record._status);
  const report = isDraft ? warnings : failures;
  const label = `${rel(file)}${isDraft ? ' [draft]' : ''}`;

  // --- elevation ---
  const elevation = record.elevation;
  if (elevation === null || elevation === undefined || elevation <= 0) {
    report.push(`${label}: elevation is ${elevation} (must be > 0)`);
  } else if (elevation > US_MAX_ELEVATION_FT) {
    report.push(
      `${label}: elevation ${elevation.toLocaleString()} ft exceeds the US ` +
      `maximum of ${US_MAX_ELEVATION_FT.toLocaleString()} ft (Denali) — ` +
      `likely a metres/feet unit error`
    );
  }

  // Draft records legitimately have no route yet; only published trails must.
  if (isDraft) { checked++; continue; }

  const trail = (record.trails || [])[0];
  const path = trail?.geo?.path;
  if (!trail || !Array.isArray(path) || path.length < 2) {
    failures.push(`${label}: published trail has no usable route geometry`);
    checked++;
    continue;
  }

  // --- distance vs route length ---
  const stats = trail.stats || {};
  const { distance, route_length_mi: routeLength, distance_type: type } = stats;
  if (typeof distance !== 'number' || distance <= 0) {
    failures.push(`${label}: published trail has no positive distance`);
  } else if (typeof routeLength !== 'number' || routeLength <= 0) {
    failures.push(
      `${label}: missing route_length_mi — re-run ` +
      `scripts/migrate-distance-semantics.py`
    );
  } else if (stats.distance_source === 'authored') {
    warnings.push(
      `${label}: authored distance ${distance} mi vs ${routeLength} mi of ` +
      `geometry — route coverage incomplete`
    );
  } else {
    const expected = type === 'loop' ? routeLength : routeLength * 2;
    const gap = Math.abs(distance - expected);
    const drift = gap / expected;
    if (drift > DISTANCE_TOLERANCE && gap > DISTANCE_TOLERANCE_FLOOR_MI) {
      failures.push(
        `${label}: distance ${distance} mi disagrees with ${type} route ` +
        `length ${routeLength} mi (expected ~${expected.toFixed(1)} mi, ` +
        `off by ${(drift * 100).toFixed(0)}%)`
      );
    }
  }
  checked++;
}

const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;

if (warnings.length) {
  console.warn(`\n⚠ ${plural(warnings.length, 'data warning')} (not blocking):`);
  for (const w of warnings.slice(0, 15)) console.warn(`   · ${w}`);
  if (warnings.length > 15) console.warn(`   … and ${warnings.length - 15} more`);
}

if (failures.length) {
  console.error(`\n❌ Build blocked: ${plural(failures.length, 'trail-data violation')}\n`);
  for (const f of failures) console.error(`   · ${f}`);
  console.error('\nFix the data (or the ingest script that produced it) and rebuild.\n');
  process.exit(1);
}

console.log(`✅ trail data validated — ${plural(checked, 'record')}, 0 violations` +
            (warnings.length ? `, ${plural(warnings.length, 'warning')}` : ''));
