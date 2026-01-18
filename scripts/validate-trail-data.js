/**
 * Trail Data Validation Script
 *
 * Purpose: Ensure all trail JSON files meet quality standards
 * Run: node scripts/validate-trail-data.js
 *
 * Checks:
 * - Required fields present
 * - GPS coordinates valid
 * - Elevations realistic
 * - Distances reasonable
 * - Data sources documented
 * - Verification dates current
 */

import { readdir, readFile } from 'fs/promises';
import { join, relative } from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const DATA_DIR = join(__dirname, '../website/src/data');

// Validation rules
const VALIDATION_RULES = {
  // GPS coordinates (continental US + Alaska + Hawaii)
  lat: { min: 18.0, max: 72.0 },  // Hawaii to Alaska
  lon: { min: -180.0, max: -65.0 }, // Alaska to Maine

  // Elevation (feet)
  elevation: { min: -282, max: 20320 }, // Death Valley to Denali

  // Trail distance (miles)
  distance: { min: 0.1, max: 50 }, // Flag if > 30 miles
  distance_warning: 30,

  // Elevation gain (feet)
  gain: { min: 0, max: 15000 }, // Flag if > 10000
  gain_warning: 10000,

  // Data verification age (days)
  verification_max_age: 547, // 18 months
  verification_warning_age: 365, // 12 months
};

// Required fields for all trails
const REQUIRED_FIELDS = [
  'name',
  'slug',
  'lat',
  'lon',
  'elevation',
  'state_slug',
];

// Recommended fields (warnings if missing)
const RECOMMENDED_FIELDS = [
  'generated_description',
  'mountain_hero',
  'seo.meta_title',
  'seo.meta_description',
  'data_sources', // CRITICAL for authenticity
];

// Results tracking
const results = {
  totalFiles: 0,
  passed: 0,
  warnings: 0,
  errors: 0,
  issues: [],
};

/**
 * Validate a single trail JSON file
 */
async function validateTrailFile(filePath, stateName) {
  try {
    const content = await readFile(filePath, 'utf-8');
    const trail = JSON.parse(content);
    const relPath = relative(DATA_DIR, filePath);
    const issues = [];

    // Check required fields
    for (const field of REQUIRED_FIELDS) {
      if (!getNestedValue(trail, field)) {
        issues.push({
          type: 'error',
          field,
          message: `Missing required field: ${field}`,
        });
      }
    }

    // Check recommended fields
    for (const field of RECOMMENDED_FIELDS) {
      if (!getNestedValue(trail, field)) {
        issues.push({
          type: 'warning',
          field,
          message: `Missing recommended field: ${field}`,
        });
      }
    }

    // Validate GPS coordinates
    if (trail.lat) {
      if (trail.lat < VALIDATION_RULES.lat.min || trail.lat > VALIDATION_RULES.lat.max) {
        issues.push({
          type: 'error',
          field: 'lat',
          message: `Latitude ${trail.lat} is out of valid range (${VALIDATION_RULES.lat.min} to ${VALIDATION_RULES.lat.max})`,
        });
      }
    }

    if (trail.lon) {
      if (trail.lon < VALIDATION_RULES.lon.min || trail.lon > VALIDATION_RULES.lon.max) {
        issues.push({
          type: 'error',
          field: 'lon',
          message: `Longitude ${trail.lon} is out of valid range (${VALIDATION_RULES.lon.min} to ${VALIDATION_RULES.lon.max})`,
        });
      }
    }

    // Validate elevation
    if (trail.elevation) {
      if (trail.elevation < VALIDATION_RULES.elevation.min || trail.elevation > VALIDATION_RULES.elevation.max) {
        issues.push({
          type: 'error',
          field: 'elevation',
          message: `Elevation ${trail.elevation} ft is unrealistic (${VALIDATION_RULES.elevation.min} to ${VALIDATION_RULES.elevation.max})`,
        });
      }

      // Check if elevation is suspiciously round
      if (trail.elevation % 100 === 0 && trail.elevation > 1000) {
        issues.push({
          type: 'warning',
          field: 'elevation',
          message: `Elevation ${trail.elevation} ft is rounded to nearest 100 - may not be precise. Verify with USGS benchmark.`,
        });
      }
    }

    // Validate trails array
    if (trail.trails && Array.isArray(trail.trails)) {
      trail.trails.forEach((t, idx) => {
        // Check distance
        if (t.distance) {
          if (t.distance < VALIDATION_RULES.distance.min || t.distance > VALIDATION_RULES.distance.max) {
            issues.push({
              type: 'error',
              field: `trails[${idx}].distance`,
              message: `Trail distance ${t.distance} mi is out of range`,
            });
          }
          if (t.distance > VALIDATION_RULES.distance_warning) {
            issues.push({
              type: 'warning',
              field: `trails[${idx}].distance`,
              message: `Trail distance ${t.distance} mi is very long - verify accuracy`,
            });
          }
        }

        // Check elevation gain
        if (t.elevation_gain) {
          if (t.elevation_gain < VALIDATION_RULES.gain.min || t.elevation_gain > VALIDATION_RULES.gain.max) {
            issues.push({
              type: 'error',
              field: `trails[${idx}].elevation_gain`,
              message: `Elevation gain ${t.elevation_gain} ft is unrealistic`,
            });
          }
          if (t.elevation_gain > VALIDATION_RULES.gain_warning) {
            issues.push({
              type: 'warning',
              field: `trails[${idx}].elevation_gain`,
              message: `Elevation gain ${t.elevation_gain} ft is extreme - verify accuracy`,
            });
          }
        }
      });
    }

    // Check data sources (CRITICAL for authenticity)
    if (!trail.data_sources) {
      issues.push({
        type: 'warning',
        field: 'data_sources',
        message: '⚠️ CRITICAL: No data_sources object - cannot verify authenticity. See DATA_QUALITY_SYSTEM.md',
      });
    } else {
      // Validate data_sources structure
      if (!trail.data_sources.verified_by) {
        issues.push({
          type: 'warning',
          field: 'data_sources.verified_by',
          message: 'Missing source attribution (e.g., "National Park Service")',
        });
      }

      if (!trail.data_sources.primary_url) {
        issues.push({
          type: 'warning',
          field: 'data_sources.primary_url',
          message: 'Missing primary_url - need link to official source',
        });
      }

      if (!trail.data_sources.verification_date) {
        issues.push({
          type: 'warning',
          field: 'data_sources.verification_date',
          message: 'Missing verification_date - when was this data last checked?',
        });
      } else {
        // Check if verification is recent
        const verificationDate = new Date(trail.data_sources.verification_date);
        const daysSinceVerification = (Date.now() - verificationDate) / (1000 * 60 * 60 * 24);

        if (daysSinceVerification > VALIDATION_RULES.verification_max_age) {
          issues.push({
            type: 'error',
            field: 'data_sources.verification_date',
            message: `Data verified ${Math.floor(daysSinceVerification)} days ago (${trail.data_sources.verification_date}) - TOO OLD. Re-verify required.`,
          });
        } else if (daysSinceVerification > VALIDATION_RULES.verification_warning_age) {
          issues.push({
            type: 'warning',
            field: 'data_sources.verification_date',
            message: `Data verified ${Math.floor(daysSinceVerification)} days ago - consider re-verifying soon`,
          });
        }
      }
    }

    // Track results
    results.totalFiles++;
    if (issues.length === 0) {
      results.passed++;
      console.log(`✅ ${relPath}`);
    } else {
      const hasErrors = issues.some(i => i.type === 'error');
      if (hasErrors) {
        results.errors++;
        console.log(`❌ ${relPath}`);
      } else {
        results.warnings++;
        console.log(`⚠️  ${relPath}`);
      }

      results.issues.push({
        file: relPath,
        trail: trail.name,
        issues,
      });
    }

  } catch (error) {
    results.totalFiles++;
    results.errors++;
    console.error(`❌ ${relative(DATA_DIR, filePath)} - PARSE ERROR: ${error.message}`);
    results.issues.push({
      file: relative(DATA_DIR, filePath),
      trail: 'UNKNOWN',
      issues: [{ type: 'error', field: 'file', message: `Parse error: ${error.message}` }],
    });
  }
}

/**
 * Get nested object value by dot notation
 */
function getNestedValue(obj, path) {
  return path.split('.').reduce((current, key) => current?.[key], obj);
}

/**
 * Scan all trail JSON files
 */
async function scanAllTrails() {
  try {
    const states = await readdir(DATA_DIR);

    for (const state of states) {
      const statePath = join(DATA_DIR, state);
      const stat = await readdir(statePath, { withFileTypes: true });

      const jsonFiles = stat.filter(f => f.isFile() && f.name.endsWith('.json'));

      for (const file of jsonFiles) {
        await validateTrailFile(join(statePath, file.name), state);
      }
    }
  } catch (error) {
    console.error('Error scanning trails:', error.message);
    process.exit(1);
  }
}

/**
 * Print detailed report
 */
function printReport() {
  console.log('\n' + '='.repeat(80));
  console.log('TRAIL DATA VALIDATION REPORT');
  console.log('='.repeat(80));
  console.log(`Total Files: ${results.totalFiles}`);
  console.log(`✅ Passed: ${results.passed}`);
  console.log(`⚠️  Warnings: ${results.warnings}`);
  console.log(`❌ Errors: ${results.errors}`);
  console.log('='.repeat(80));

  if (results.issues.length > 0) {
    console.log('\nDETAILED ISSUES:\n');

    for (const item of results.issues) {
      console.log(`\n📄 ${item.file} (${item.trail})`);

      for (const issue of item.issues) {
        const icon = issue.type === 'error' ? '❌' : '⚠️ ';
        console.log(`   ${icon} [${issue.field}] ${issue.message}`);
      }
    }
  }

  console.log('\n' + '='.repeat(80));
  console.log('RECOMMENDATIONS:');
  console.log('='.repeat(80));

  const missingDataSources = results.issues.filter(i =>
    i.issues.some(iss => iss.field === 'data_sources')
  ).length;

  if (missingDataSources > 0) {
    console.log(`\n⚠️  ${missingDataSources} trails missing data_sources attribution`);
    console.log('   Action: Add data_sources object to verify authenticity');
    console.log('   See: DATA_QUALITY_SYSTEM.md for format\n');
  }

  const oldVerifications = results.issues.filter(i =>
    i.issues.some(iss => iss.field === 'data_sources.verification_date' && iss.type === 'error')
  ).length;

  if (oldVerifications > 0) {
    console.log(`\n❌ ${oldVerifications} trails have outdated verification (>18 months)`);
    console.log('   Action: Re-verify against official sources and update verification_date\n');
  }

  console.log('\n' + '='.repeat(80));

  // Exit code based on results
  if (results.errors > 0) {
    console.log('❌ VALIDATION FAILED - Fix errors before deployment\n');
    process.exit(1);
  } else if (results.warnings > 0) {
    console.log('⚠️  VALIDATION PASSED WITH WARNINGS - Review recommended\n');
    process.exit(0);
  } else {
    console.log('✅ ALL CHECKS PASSED - Data quality excellent!\n');
    process.exit(0);
  }
}

/**
 * Main execution
 */
async function main() {
  console.log('🔍 Starting trail data validation...\n');
  await scanAllTrails();
  printReport();
}

main();
