# Data Quality & Authenticity System

**Last Updated:** January 2026
**Purpose:** Ensure all trail data on SummitSeeker.io is accurate, verifiable, and trustworthy.

---

## 🎯 Data Quality Philosophy

As a trail information provider, we have a **responsibility to hikers' safety**. Inaccurate data can lead to:
- Hikers being unprepared for trail difficulty
- Wrong gear for conditions
- Safety issues from incorrect GPS coordinates
- Wasted time/gas driving to wrong locations

**Our Commitment:** Every trail must be verified against authoritative sources before publication.

---

## 📊 Data Validation Requirements

### 1. Required Fields (Must Be Accurate)

| Field | Validation Method | Source Authority |
|-------|------------------|------------------|
| **GPS Coordinates** | Must match official sources within 0.001° (~100m) | USGS, NPS, USFS maps |
| **Elevation** | Must match USGS topo data within 10 feet | USGS, PeakBagger, official park data |
| **Trail Distance** | Must match official trail data within 0.2 miles | NPS, USFS, state park websites |
| **Elevation Gain** | Must match official data within 100 feet | CalTopo, official sources |
| **Trailhead Parking** | GPS must be verified, fee info current | Official park websites |
| **Permit Requirements** | Must be current (check annually) | Recreation.gov, park websites |

### 2. Acceptable Data Sources (In Order of Priority)

#### ✅ TIER 1: Official Government Sources (100% Trusted)
- **National Park Service (NPS)** - nps.gov
- **US Forest Service (USFS)** - fs.usda.gov
- **USGS Topographic Maps** - usgs.gov
- **State Park Systems** - Official state websites
- **Recreation.gov** - Official federal recreation site

#### ✅ TIER 2: Verified Community Sources (Must Cross-Reference)
- **PeakBagger.com** - For elevations and summit coordinates
- **CalTopo** - For elevation profiles and GPS tracks
- **Gaia GPS** - For verified trail routes
- **SummitPost** - For route descriptions (verify dates)

#### ❌ TIER 3: DO NOT USE as Primary Sources
- **AllTrails** - Copyrighted data, user-generated distances often inaccurate
- **Wikipedia** - Unverified, can be edited by anyone
- **Blogs/Personal Websites** - Not authoritative
- **AI-Generated Content** - Never use without verification

### 3. Data Verification Checklist

**Before adding ANY trail, complete this checklist:**

- [ ] **Source Documentation**
  - [ ] Primary source URL recorded in `data_sources.verified_by` field
  - [ ] Date of verification recorded
  - [ ] Backup source identified (if primary changes)

- [ ] **GPS Accuracy**
  - [ ] Summit/destination coordinates verified on USGS topo map
  - [ ] Trailhead parking coordinates tested on Google Maps
  - [ ] Coordinates match official NPS/USFS data

- [ ] **Physical Stats**
  - [ ] Elevation matches USGS benchmark data
  - [ ] Distance matches official trail signs or park data
  - [ ] Elevation gain calculated from topo map or CalTopo

- [ ] **Current Information**
  - [ ] Permit requirements checked within last 30 days
  - [ ] Parking fees verified on official website
  - [ ] Seasonal closures/restrictions noted
  - [ ] Trail conditions checked (recent reports)

- [ ] **Safety Information**
  - [ ] Emergency contact numbers verified
  - [ ] Hazards documented from official sources
  - [ ] Difficulty rating based on objective criteria (not opinion)

---

## 🔍 Data Source Attribution Format

Every trail JSON file **MUST** include a `data_sources` object:

```json
{
  "name": "Half Dome",
  "data_sources": {
    "verified_by": "National Park Service",
    "primary_url": "https://www.nps.gov/yose/planyourvisit/halfdome.htm",
    "verification_date": "2026-01-15",
    "elevation_source": "USGS Benchmark",
    "gps_source": "NPS Official Map",
    "notes": "Permit info updated annually; distance from NPS trail sign at trailhead"
  }
}
```

**Required Fields:**
- `verified_by`: Name of authoritative source
- `primary_url`: Direct link to source data
- `verification_date`: When we last checked (YYYY-MM-DD)
- `elevation_source`: Where elevation came from
- `gps_source`: Source for coordinates

---

## 🛠️ Validation Tools

### Automated Validation Script

Run before every deployment:

```bash
node scripts/validate-trail-data.js
```

**Checks:**
1. All required fields present
2. GPS coordinates in valid range
3. Elevation > 0 and < 30,000 ft
4. Distance > 0 and < 50 miles (flag if >30)
5. `data_sources` object exists
6. `verification_date` within last 12 months

### Manual Review Process

**New Trails:**
1. Researcher adds trail with sources documented
2. Reviewer cross-checks 3 data points against official sources
3. Test GPS coordinates on Google Maps
4. Senior editor approves before merge

**Existing Trails:**
- Annual review of all trails
- Update verification_date when re-checked
- Flag trails with verification_date > 18 months old

---

## 📝 Common Data Quality Issues

### Issue 1: User-Generated Distances
**Problem:** AllTrails shows 8.2 mi, official NPS says 7.8 mi
**Solution:** Always use NPS data. Note discrepancy in trail description.

### Issue 2: Parking GPS vs Trailhead GPS
**Problem:** Parking lot vs actual trail start point
**Solution:** Use parking lot GPS in `parking` field, trailhead GPS in main `lat/lon`

### Issue 3: Seasonal Elevation Changes
**Problem:** Snow adds "height" to summit
**Solution:** Use USGS benchmark elevation, not seasonal measurements

### Issue 4: Multiple Trail Routes
**Problem:** Half Dome has 3 different routes with different distances
**Solution:** Document most popular route, mention alternatives in description

---

## 🚨 Red Flags - Data to Question

| Red Flag | Why It's Suspicious | Action |
|----------|---------------------|--------|
| Elevation ends in 0 | Rounded, not precise | Find USGS benchmark |
| Distance is identical to AllTrails | May be copied | Verify with official source |
| No permit info for popular peak | Probably outdated | Check Recreation.gov |
| GPS coordinates have < 4 decimal places | Too imprecise | Get exact coordinates |
| "Approximately X miles" | Not measured | Find official distance |

---

## 🎓 Training Resources

### For Content Team

**Required Reading:**
1. [USGS Topo Map Reading](https://www.usgs.gov/educational-resources/topographic-map-symbols)
2. [NPS Trail Data Standards](https://www.nps.gov/)
3. [CalTopo Tutorial](https://caltopo.com/tutorials/)

**How to Verify:**
- **Elevation:** Search "[Peak Name] USGS" → Find benchmark data
- **Distance:** Check official park website → Trail descriptions
- **GPS:** Use USGS TopoView → Match to topo map
- **Permits:** Search "[Trail Name] permit" → Official .gov site only

---

## 📅 Maintenance Schedule

| Task | Frequency | Responsible |
|------|-----------|-------------|
| Validate new trails | Before publication | Content Reviewer |
| Re-verify existing trails | Annually | Data Team |
| Update permit info | Every 3 months | Permits Coordinator |
| Check for trail closures | Monthly | Operations |
| Run validation script | Every deployment | CI/CD Pipeline |

---

## ✅ Data Quality Metrics

**Target Goals:**
- ✅ 100% of trails have `data_sources` documented
- ✅ 100% of trails verified within 18 months
- ✅ 0 validation errors in automated checks
- ✅ GPS accuracy within 100 meters of official data
- ✅ Elevation accuracy within 10 feet

**Current Status (as of 2026-01-18):**
- Total trails: 138
- With data_sources: **0** ⚠️ (Need to add retroactively)
- Verified within 12 months: **15** (California trails - Jan 2026)
- Validation errors: TBD (need to run script)

---

## 🔧 Next Steps

1. **Create validation script** (`scripts/validate-trail-data.js`)
2. **Add `data_sources` to all California trails** (15 trails)
3. **Retroactively add sources to New England trails** (123 trails)
4. **Set up automated checks in CI/CD**
5. **Create public "Data Sources" page** on website for transparency

---

## 📞 Questions?

If you're unsure about a data point:
1. **Don't guess** - mark as "needs verification"
2. **Ask in Slack #data-quality** channel
3. **Document uncertainty** in trail notes
4. **Use conservative estimates** (harder difficulty if uncertain)

**Remember:** A blank field is better than wrong information.

---

*This document is a living standard. Update it as we learn better validation methods.*
