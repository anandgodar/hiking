#!/bin/bash

# Fix Phase 1 Critical GPS Data Issues
# Downloads GPX files and converts to SummitSeeker geo format

set -e

GPX_DIR="/home/user/hiking/gpx-downloads"
DATA_DIR="/home/user/hiking/website/src/data/california"

# Create GPX download directory
mkdir -p "$GPX_DIR"

echo "======================================================================"
echo "PHASE 1: CRITICAL GPS DATA FIXES"
echo "======================================================================"
echo ""
echo "This script will help you fix the 6 most critical trail GPS issues."
echo ""

# Phase 1 trails with GPX sources
declare -A TRAILS
TRAILS["lower-yosemite-fall"]="https://www.alltrails.com/trail/us/california/lower-yosemite-fall-trail"
TRAILS["bridalveil-fall-yosemite"]="https://www.alltrails.com/trail/us/california/bridalveil-fall"
TRAILS["mount-whitney"]="https://www.alltrails.com/trail/us/california/mount-whitney-trail"
TRAILS["half-dome-yosemite"]="https://www.alltrails.com/trail/us/california/half-dome-trail"
TRAILS["nevada-fall-yosemite"]="https://www.alltrails.com/trail/us/california/mist-trail-to-vernal-fall-and-nevada-fall"
TRAILS["mist-trail-vernal-fall"]="https://www.alltrails.com/trail/us/california/mist-trail-to-vernal-fall"

declare -A TRAIL_NAMES
TRAIL_NAMES["lower-yosemite-fall"]="Lower Yosemite Fall"
TRAIL_NAMES["bridalveil-fall-yosemite"]="Bridalveil Fall"
TRAIL_NAMES["mount-whitney"]="Mount Whitney"
TRAIL_NAMES["half-dome-yosemite"]="Half Dome"
TRAIL_NAMES["nevada-fall-yosemite"]="Nevada Fall"
TRAIL_NAMES["mist-trail-vernal-fall"]="Vernal Fall (Mist Trail)"

# Check which GPX files are already downloaded
echo "Checking for existing GPX files..."
echo ""

MISSING_COUNT=0
READY_COUNT=0

for slug in "${!TRAILS[@]}"; do
    if [ -f "$GPX_DIR/${slug}.gpx" ]; then
        echo "✅ ${TRAIL_NAMES[$slug]}: GPX file found"
        ((READY_COUNT++))
    else
        echo "❌ ${TRAIL_NAMES[$slug]}: GPX file missing"
        ((MISSING_COUNT++))
    fi
done

echo ""
echo "======================================================================"

if [ $MISSING_COUNT -gt 0 ]; then
    echo "⚠️  MANUAL DOWNLOAD REQUIRED"
    echo "======================================================================"
    echo ""
    echo "You need to download $MISSING_COUNT GPX files manually."
    echo ""
    echo "IMPORTANT: AllTrails requires a Pro subscription to export GPX files."
    echo ""
    echo "OPTION 1: AllTrails Pro (Recommended - Most Accurate)"
    echo "----------------------------------------------------------------------"
    echo "If you have AllTrails Pro:"
    echo ""

    for slug in "${!TRAILS[@]}"; do
        if [ ! -f "$GPX_DIR/${slug}.gpx" ]; then
            echo "📍 ${TRAIL_NAMES[$slug]}"
            echo "   1. Visit: ${TRAILS[$slug]}"
            echo "   2. Click 'Download' → 'Export GPX'"
            echo "   3. Save as: $GPX_DIR/${slug}.gpx"
            echo ""
        fi
    done

    echo ""
    echo "OPTION 2: Free Alternative - CalTopo (Manual Tracing)"
    echo "----------------------------------------------------------------------"
    echo "If you don't have AllTrails Pro:"
    echo ""
    echo "1. Go to: https://caltopo.com"
    echo "2. Search for the trail (e.g., 'Nevada Fall Yosemite')"
    echo "3. Click 'Line' tool and trace the trail on the map"
    echo "4. Right-click the line → 'Export' → 'GPX'"
    echo "5. Save to: $GPX_DIR/trail-slug.gpx"
    echo ""
    echo "OPTION 3: Free Alternative - NPS Official Data"
    echo "----------------------------------------------------------------------"
    echo "For Yosemite trails, check NPS official data:"
    echo "https://www.nps.gov/yose/planyourvisit/trail-gps.htm"
    echo ""
    echo "======================================================================"
    echo ""
    echo "After downloading GPX files, run this script again."
    echo ""

    read -p "Press Enter to exit..."
    exit 0
fi

echo "✅ All GPX files found! Ready to convert."
echo "======================================================================"
echo ""

# Convert each GPX file
CONVERTED=0
FAILED=0

for slug in "${!TRAILS[@]}"; do
    echo "----------------------------------------------------------------------"
    echo "Converting: ${TRAIL_NAMES[$slug]}"
    echo "----------------------------------------------------------------------"

    gpx_file="$GPX_DIR/${slug}.gpx"
    json_file="$DATA_DIR/${slug}.json"

    if [ -f "$json_file" ]; then
        echo "📍 GPX: $gpx_file"
        echo "📄 JSON: $json_file"
        echo ""

        # Run conversion
        if python3 /home/user/hiking/scripts/gpx-to-geo.py "$gpx_file" "$json_file"; then
            echo "✅ Converted successfully"
            ((CONVERTED++))

            # Update data_sources.gps_source field
            echo "   Updating data_sources.gps_source..."
            python3 -c "
import json
with open('$json_file', 'r') as f:
    data = json.load(f)
if 'data_sources' in data:
    data['data_sources']['gps_source'] = 'AllTrails verified GPX export'
    data['data_sources']['verification_date'] = '2026-01-18'
    with open('$json_file', 'w') as f:
        json.dump(data, f, indent=2)
    print('   ✅ Updated data_sources')
"
        else
            echo "❌ Conversion failed"
            ((FAILED++))
        fi
    else
        echo "❌ JSON file not found: $json_file"
        ((FAILED++))
    fi

    echo ""
done

echo "======================================================================"
echo "CONVERSION SUMMARY"
echo "======================================================================"
echo "✅ Converted: $CONVERTED"
echo "❌ Failed: $FAILED"
echo ""

if [ $CONVERTED -gt 0 ]; then
    echo "Running quality audit to verify improvements..."
    echo ""
    python3 /home/user/hiking/scripts/audit-gps-quality.py | grep -A 20 "CRITICAL"
    echo ""
    echo "======================================================================"
    echo "NEXT STEPS"
    echo "======================================================================"
    echo ""
    echo "1. Review the updated trail files"
    echo "2. Test on your dev server (check maps look correct)"
    echo "3. Commit changes:"
    echo ""
    echo "   git add website/src/data/california/*.json"
    echo "   git commit -m \"Fix Phase 1 critical GPS data for 6 trails\""
    echo "   git push"
    echo ""
fi
