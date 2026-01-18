# GPS Data Quality - Fix Priority List

**Audit Date:** 2026-01-18
**Total Trails Analyzed:** 138
**Trails Needing Fixes:** 16 (15 POOR, 1 FAIR)

## Summary

- ✅ **GOOD (80-100):** 122 trails - No action needed
- ⚠️  **FAIR (50-79):** 1 trail - Low priority
- 🔴 **POOR (<50):** 15 trails - **IMMEDIATE ACTION REQUIRED**

## Critical Issues Found

All 15 California trails have **severely oversimplified GPS paths**:
- Average: **1.0 points per mile** (should be 15+)
- Missing elevation data
- Paths are too straight (missing switchbacks/curves)
- Chart data minimal or missing

## 🔴 HIGHEST PRIORITY FIXES (California)

### 1. **Lower Yosemite Fall** - CRITICAL
- **Score:** 0/100
- **Issue:** No GPS path data at all
- **GPX Source:** https://www.alltrails.com/trail/us/california/lower-yosemite-fall-trail
- **Distance:** 1.2 mi
- **Fix Priority:** 🔴 IMMEDIATE

### 2. **Bridalveil Fall** - CRITICAL
- **Score:** 0/100
- **Issue:** No GPS path data at all
- **GPX Source:** https://www.alltrails.com/trail/us/california/bridalveil-fall
- **Distance:** 0.5 mi
- **Fix Priority:** 🔴 IMMEDIATE

### 3. **Mount Whitney** - CRITICAL
- **Score:** 20/100
- **GPS Density:** 0.3 pts/mi (need 15+)
- **GPX Source:** https://www.alltrails.com/trail/us/california/mount-whitney-trail
- **Distance:** 22.0 mi
- **Issues:** Most popular trail in CA, highest peak - MUST be accurate
- **Fix Priority:** 🔴 IMMEDIATE

### 4. **Half Dome** - CRITICAL
- **Score:** 20/100
- **GPS Density:** 0.7 pts/mi (need 15+)
- **GPX Source:** https://www.alltrails.com/trail/us/california/half-dome-trail
- **Distance:** 14.2 mi
- **Issues:** Iconic Yosemite trail - MUST be accurate
- **Fix Priority:** 🔴 IMMEDIATE

### 5. **Nevada Fall** - CRITICAL *(User reported)*
- **Score:** 15/100
- **GPS Density:** 1.2 pts/mi (need 15+)
- **GPX Source:** https://www.alltrails.com/trail/us/california/mist-trail-to-vernal-fall-and-nevada-fall
- **Distance:** 6.9 mi
- **Issues:** Map and elevation profile look wrong (user reported)
- **Fix Priority:** 🔴 IMMEDIATE

### 6. **Vernal Fall (Mist Trail)** - CRITICAL
- **Score:** 20/100
- **GPS Density:** 1.1 pts/mi (need 15+)
- **GPX Source:** https://www.alltrails.com/trail/us/california/mist-trail-to-vernal-fall
- **Distance:** 5.4 mi
- **Fix Priority:** 🔴 IMMEDIATE

### 7. **Upper Yosemite Fall** - HIGH
- **Score:** 20/100
- **GPS Density:** 1.0 pts/mi (need 15+)
- **GPX Source:** https://www.alltrails.com/trail/us/california/upper-yosemite-falls-trail
- **Distance:** 7.2 mi
- **Fix Priority:** 🟠 HIGH

### 8. **Clouds Rest** - HIGH
- **Score:** 20/100
- **GPS Density:** 0.4 pts/mi (need 15+)
- **GPX Source:** https://www.alltrails.com/trail/us/california/clouds-rest-trail
- **Distance:** 14.5 mi
- **Fix Priority:** 🟠 HIGH

### 9. **Cathedral Lakes** - HIGH
- **Score:** 25/100
- **GPS Density:** 0.6 pts/mi (need 15+)
- **GPX Source:** https://www.alltrails.com/trail/us/california/cathedral-lakes-trail
- **Distance:** 8.0 mi
- **Fix Priority:** 🟠 HIGH

### 10. **Sentinel Dome & Taft Point** - MEDIUM
- **Score:** 25/100
- **GPS Density:** 1.4 pts/mi (need 15+)
- **GPX Source:** https://www.alltrails.com/trail/us/california/taft-point-and-the-fissures-via-pohono-trail
- **Distance:** 5.0 mi
- **Fix Priority:** 🟡 MEDIUM

### 11. **Panorama Trail** - MEDIUM
- **Score:** 30/100
- **GPS Density:** 0.7 pts/mi (need 15+)
- **GPX Source:** https://www.alltrails.com/trail/us/california/panorama-trail
- **Distance:** 8.5 mi
- **Fix Priority:** 🟡 MEDIUM

### 12. **Mirror Lake** - MEDIUM
- **Score:** 25/100
- **GPS Density:** 1.4 pts/mi (need 15+)
- **GPX Source:** https://www.alltrails.com/trail/us/california/mirror-lake-loop-trail
- **Distance:** 5.0 mi
- **Fix Priority:** 🟡 MEDIUM

### 13. **May Lake** - MEDIUM
- **Score:** 15/100
- **GPS Density:** 2.1 pts/mi (need 15+)
- **GPX Source:** https://www.alltrails.com/trail/us/california/may-lake-trail
- **Distance:** 2.4 mi
- **Fix Priority:** 🟡 MEDIUM

### 14. **Mission Peak** - MEDIUM
- **Score:** 20/100
- **GPS Density:** 1.1 pts/mi (need 15+)
- **GPX Source:** https://www.alltrails.com/trail/us/california/mission-peak-loop
- **Distance:** 6.2 mi
- **Fix Priority:** 🟡 MEDIUM

### 15. **Potato Chip Rock** - MEDIUM
- **Score:** 20/100
- **GPS Density:** 1.0 pts/mi (need 15+)
- **GPX Source:** https://www.alltrails.com/trail/us/california/potato-chip-rock-via-mt-woodson-trail
- **Distance:** 7.2 mi
- **Fix Priority:** 🟡 MEDIUM

## ⚠️ FAIR QUALITY (Low Priority)

### Mount Kearsarge (NH)
- **Score:** 70/100
- **GPS Density:** 15.0 pts/mi (just at threshold)
- **Fix Priority:** 🟢 LOW - acceptable quality

## Recommended Fix Strategy

### Phase 1: Critical Trails (Week 1)
Fix these 6 trails FIRST (user-facing issues + most popular):
1. Lower Yosemite Fall (no data)
2. Bridalveil Fall (no data)
3. Mount Whitney (highest peak, very popular)
4. Half Dome (iconic, very popular)
5. Nevada Fall (user reported issue)
6. Vernal Fall (Mist Trail - very popular)

### Phase 2: High-Priority Trails (Week 2)
7. Upper Yosemite Fall
8. Clouds Rest
9. Cathedral Lakes

### Phase 3: Medium-Priority Trails (Week 3)
10-15. Remaining California trails

## How to Fix

### For each trail:

```bash
# 1. Download GPX from AllTrails (see GPX Source URLs above)
# 2. Convert using our tool:
python3 scripts/gpx-to-geo.py trail.gpx \\
  website/src/data/california/trail-name.json

# 3. Validate:
python3 scripts/audit-gps-quality.py

# 4. Verify on map (run dev server and check trail page)

# 5. Commit:
git add website/src/data/california/trail-name.json
git commit -m "Fix GPS data for Trail Name - add accurate path"
```

## Alternative GPX Sources

If AllTrails doesn't work:
1. **CalTopo** - https://caltopo.com (trace manually)
2. **Gaia GPS** - https://www.gaiagps.com
3. **NPS Official Data** - https://www.nps.gov/yose/planyourvisit/trail-gps.htm
4. **Hiking Project** - https://www.hikingproject.com

## Success Metrics

After fixes, each trail should have:
- ✅ GPS Density: **15+ points per mile**
- ✅ Elevation data on every point
- ✅ Chart: **10+ elevation profile points**
- ✅ Quality Score: **80+/100**
- ✅ Path follows actual trail (not straight lines)

## Notes

- **Do NOT** use AI-generated GPS data
- **Do NOT** guess coordinates
- **ALWAYS** verify with official sources
- **ALWAYS** test on map before committing
- Update `data_sources.gps_source` field when fixing

## Full Audit Report

See: `/home/user/hiking/gps-audit-report.json`
