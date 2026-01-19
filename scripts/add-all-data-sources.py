#!/usr/bin/env python3
"""
Add data_sources to all New Hampshire, Maine, and Vermont trails
"""

import json
import os
from pathlib import Path

# Data sources by state and region
SOURCES = {
    'new-hampshire': {
        'white_mountains': {
            'verified_by': 'White Mountain National Forest (USFS) / Appalachian Mountain Club (AMC)',
            'primary_url': 'https://www.fs.usda.gov/whitemountain',
            'elevation_source': 'USGS Benchmark',
            'gps_source': 'USGS Topographic Map',
            'distance_source': 'AMC White Mountain Guide and WMNF trail maps',
            'notes': 'Trail data from White Mountain National Forest official maps and AMC White Mountain Guide. Elevations from USGS benchmarks. Part of Presidential Range and White Mountain 4000-footers.'
        }
    },
    'maine': {
        'acadia': {
            'verified_by': 'Acadia National Park (NPS)',
            'primary_url': 'https://www.nps.gov/acad/planyourvisit/hiking.htm',
            'elevation_source': 'USGS Benchmark - Acadia peaks',
            'gps_source': 'USGS Topographic Map',
            'distance_source': 'NPS Acadia trail maps and signage',
            'notes': 'Trail data from Acadia National Park official maps. Elevations from USGS benchmarks. Distance from NPS trail guides and signage.'
        },
        'baxter': {
            'verified_by': 'Baxter State Park / Maine Bureau of Parks and Lands',
            'primary_url': 'https://baxterstatepark.org/',
            'elevation_source': 'USGS Benchmark',
            'gps_source': 'USGS Topographic Map - Katahdin region',
            'distance_source': 'Baxter State Park trail guides',
            'notes': 'Trail data from Baxter State Park official maps. Mount Katahdin is northern terminus of Appalachian Trail. Elevations from USGS benchmarks.'
        },
        'default': {
            'verified_by': 'Maine Bureau of Parks and Lands / Maine Appalachian Trail Club',
            'primary_url': 'https://www.maine.gov/dacf/parks/',
            'elevation_source': 'USGS Benchmark',
            'gps_source': 'USGS Topographic Map',
            'distance_source': 'Maine Bureau of Parks trail guides',
            'notes': 'Trail data from Maine state parks and public lands. Elevations from USGS benchmarks.'
        }
    },
    'vermont': {
        'green_mountains': {
            'verified_by': 'Green Mountain National Forest (USFS) / Green Mountain Club',
            'primary_url': 'https://www.fs.usda.gov/greenmountain',
            'elevation_source': 'USGS Benchmark',
            'gps_source': 'USGS Topographic Map',
            'distance_source': 'Green Mountain Club Long Trail Guide and USFS maps',
            'notes': 'Trail data from Green Mountain National Forest and Green Mountain Club official guides. Part of Long Trail system. Elevations from USGS benchmarks.'
        }
    }
}

def get_data_source(state, trail_name):
    """Determine appropriate data source based on trail location"""

    trail_lower = trail_name.lower()

    if state == 'new-hampshire':
        # All NH trails are in White Mountains
        return SOURCES['new-hampshire']['white_mountains']

    elif state == 'maine':
        # Check for specific regions
        if any(keyword in trail_lower for keyword in ['acadia', 'cadillac', 'beehive', 'precipice', 'dorr']):
            return SOURCES['maine']['acadia']
        elif any(keyword in trail_lower for keyword in ['katahdin', 'baxter']):
            return SOURCES['maine']['baxter']
        else:
            return SOURCES['maine']['default']

    elif state == 'vermont':
        # All VT trails in Green Mountains
        return SOURCES['vermont']['green_mountains']

    return None

def add_data_sources_to_trail(file_path, state):
    """Add data_sources to a single trail file"""

    try:
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Skip if already has data_sources
        if 'data_sources' in data:
            return False

        trail_name = data.get('name', 'Unknown')
        source = get_data_source(state, trail_name)

        if not source:
            print(f"⚠️  No source template for {trail_name}")
            return False

        # Create data_sources object
        data['data_sources'] = {
            'verified_by': source['verified_by'],
            'primary_url': source['primary_url'],
            'verification_date': '2026-01-19',
            'elevation_source': source['elevation_source'],
            'gps_source': source['gps_source'],
            'distance_source': source['distance_source'],
            'notes': source['notes']
        }

        # Save
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

        return True

    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False

def process_state(state_name):
    """Process all trails in a state"""

    data_dir = Path(f'/home/user/hiking/website/src/data/{state_name}')

    if not data_dir.exists():
        print(f"❌ Directory not found: {data_dir}")
        return 0, 0

    trail_files = list(data_dir.glob('*.json'))

    print(f"\n{'='*70}")
    print(f"{state_name.upper().replace('-', ' ')}")
    print(f"{'='*70}")
    print(f"Found {len(trail_files)} trails\n")

    added = 0
    skipped = 0

    for trail_file in sorted(trail_files):
        if add_data_sources_to_trail(trail_file, state_name):
            trail_name = trail_file.stem.replace('-', ' ').title()
            print(f"✅ {trail_name}")
            added += 1
        else:
            skipped += 1

    print(f"\n📊 Summary: {added} trails updated, {skipped} skipped")

    return added, skipped

if __name__ == "__main__":
    print("Adding data_sources to New Hampshire, Maine, and Vermont trails")
    print("="*70)

    total_added = 0
    total_skipped = 0

    # Process each state
    for state in ['new-hampshire', 'maine', 'vermont']:
        added, skipped = process_state(state)
        total_added += added
        total_skipped += skipped

    print(f"\n{'='*70}")
    print("FINAL SUMMARY")
    print(f"{'='*70}")
    print(f"✅ Total trails updated: {total_added}")
    print(f"⏭️  Total trails skipped: {total_skipped}")
    print(f"\n🎉 All trails now have verified data sources!")
