  # Quick Start: Fix Phase 1 Critical GPS Issues

**Goal:** Fix the 6 most critical trails with accurate GPS data

## 🚀 Quick Start (5 Minutes)

### Option 1: If You Have AllTrails Pro (Easiest)

```bash
# 1. Download these 6 GPX files from AllTrails:
#    - Visit each URL below
#    - Click "Download" → "Export GPX"
#    - Save to: /home/user/hiking/gpx-downloads/

mkdir -p /home/user/hiking/gpx-downloads
cd /home/user/hiking/gpx-downloads
```

**Download these files:**

1. **Lower Yosemite Fall**
   - URL: https://www.alltrails.com/trail/us/california/lower-yosemite-fall-trail
   - Save as: `lower-yosemite-fall.gpx`

2. **Bridalveil Fall**
   - URL: https://www.alltrails.com/trail/us/california/bridalveil-fall
   - Save as: `bridalveil-fall-yosemite.gpx`

3. **Mount Whitney**
   - URL: https://www.alltrails.com/trail/us/california/mount-whitney-trail
   - Save as: `mount-whitney.gpx`

4. **Half Dome**
   - URL: https://www.alltrails.com/trail/us/california/half-dome-trail
   - Save as: `half-dome-yosemite.gpx`

5. **Nevada Fall**
   - URL: https://www.alltrails.com/trail/us/california/mist-trail-to-vernal-fall-and-nevada-fall
   - Save as: `nevada-fall-yosemite.gpx`

6. **Vernal Fall**
   - URL: https://www.alltrails.com/trail/us/california/mist-trail-to-vernal-fall
   - Save as: `mist-trail-vernal-fall.gpx`

```bash
# 2. Run the batch conversion script:
cd /home/user/hiking
./scripts/fix-phase1-gps.sh

# 3. Verify improvements:
python3 scripts/audit-gps-quality.py | head -30

# 4. Commit:
git add website/src/data/california/*.json
git commit -m "Fix Phase 1 critical GPS data for 6 trails

- Lower Yosemite Fall: Added accurate GPS path
- Bridalveil Fall: Added accurate GPS path
- Mount Whitney: Fixed oversimplified path (0.3 → 15+ pts/mi)
- Half Dome: Fixed oversimplified path (0.7 → 15+ pts/mi)
- Nevada Fall: Fixed oversimplified path (1.2 → 15+ pts/mi)
- Vernal Fall: Fixed oversimplified path (1.1 → 15+ pts/mi)

All trails now have accurate elevation profiles and proper trail curves."
git push
```

---

### Option 2: Free Alternative - CalTopo (No Subscription Required)

**For each trail:**

1. Go to https://caltopo.com
2. Search for trail name (e.g., "Nevada Fall Yosemite")
3. Click the **Line tool** (pencil icon)
4. Trace the trail on the map (follow the trail carefully)
5. Right-click the line → **"Export"** → **"GPX File"**
6. Save to `/home/user/hiking/gpx-downloads/trail-slug.gpx`

Then run the conversion script:
```bash
./scripts/fix-phase1-gps.sh
```

---

### Option 3: Free Alternative - Gaia GPS Trial

1. Sign up for free trial: https://www.gaiagps.com
2. Search for trail
3. Download GPX export
4. Run conversion script

---

### Option 4: OpenStreetMap (Most Work, But Free)

1. Go to https://www.openstreetmap.org
2. Search for trail
3. Use https://hiking.waymarkedtrails.org to find trail routes
4. Export via Overpass API
5. Convert to GPX format

---

## 📊 What You'll See After Fixing

**Before (Nevada Fall example):**
```
GPS Points: 8
Distance: 6.9 mi
Points per mile: 1.2
Quality Score: 15/100
Issues: Very low GPS density, path too straight
```

**After:**
```
GPS Points: 120+
Distance: 6.9 mi
Points per mile: 17.4
Quality Score: 95/100
Quality: GOOD ✅
```

---

## 🛠️ Manual Fix (Individual Trail)

If you only want to fix one trail:

```bash
# Download GPX for that trail

# Convert it:
python3 scripts/gpx-to-geo.py \
  /home/user/hiking/gpx-downloads/nevada-fall-yosemite.gpx \
  /home/user/hiking/website/src/data/california/nevada-fall-yosemite.json

# Check quality:
python3 scripts/audit-gps-quality.py | grep "Nevada Fall"

# Commit:
git add website/src/data/california/nevada-fall-yosemite.json
git commit -m "Fix Nevada Fall GPS data - accurate path with elevation"
git push
```

---

## ❓ Troubleshooting

### "I don't have AllTrails Pro"
Use CalTopo (Option 2) - it's free and accurate

### "The GPX file won't convert"
Check the file format:
```bash
file /home/user/hiking/gpx-downloads/trail.gpx
# Should show: "GPX GPS Exchange Format"
```

### "How do I know if the fix worked?"
Run the audit tool:
```bash
python3 scripts/audit-gps-quality.py | grep "Your Trail Name"
```

Look for:
- Quality Score: 80+ (was <50)
- Points per mile: 15+ (was <2)
- Quality: GOOD (was POOR)

### "The map still looks wrong"
1. Clear browser cache
2. Rebuild the site: `npm run build`
3. Verify the JSON file has new `geo.path` with 100+ points

---

## 📋 Checklist

Phase 1 trails to fix:

- [ ] Lower Yosemite Fall (NO GPS DATA - critical)
- [ ] Bridalveil Fall (NO GPS DATA - critical)
- [ ] Mount Whitney (0.3 pts/mi → need 15+)
- [ ] Half Dome (0.7 pts/mi → need 15+)
- [ ] Nevada Fall (1.2 pts/mi → need 15+) ← User reported issue
- [ ] Vernal Fall (1.1 pts/mi → need 15+)

After all 6 are fixed:
- [ ] Run full audit: `python3 scripts/audit-gps-quality.py`
- [ ] Check that POOR count dropped from 15 to 9
- [ ] Commit and push all changes
- [ ] Move to Phase 2 (if desired)

---

## 🎯 Success Criteria

Each trail should have:
- ✅ 15+ GPS points per mile
- ✅ Elevation data on every point (3rd coordinate)
- ✅ 10+ elevation chart points
- ✅ Quality score 80+/100
- ✅ Path follows actual trail (curves, switchbacks visible)

---

## 📞 Need Help?

1. Check `GPS_FIX_PRIORITY.md` for full details
2. Run `python3 scripts/audit-gps-quality.py` to see current status
3. Read the GPX converter help: `python3 scripts/gpx-to-geo.py --help`
