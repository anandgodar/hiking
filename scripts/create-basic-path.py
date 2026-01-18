#!/usr/bin/env python3
"""Create basic GPS path from start/summit markers"""

import json
import math
import sys

def create_path_from_markers(trail_file):
    """Create a basic GPS path from markers"""

    with open(trail_file, 'r') as f:
        data = json.load(f)

    trail_name = data.get('name', 'Unknown')
    print(f"Creating path for: {trail_name}")

    trail = data['trails'][0]
    stats = trail.get('stats', {})
    markers = trail['geo'].get('markers', {})

    start = markers.get('start')
    summit = markers.get('summit')

    if not start or not summit:
        print("❌ Missing start or summit marker")
        return False

    distance = stats.get('distance', 1.0)
    gain = stats.get('gain', 100)

    # Number of points based on distance (15 pts/mi)
    num_points = max(10, int(distance * 20))

    # Create path
    path = []
    start_ele = 4000  # Yosemite Valley elevation

    for i in range(num_points + 1):
        fraction = i / num_points

        # Interpolate lat/lon
        lat = start[0] + (summit[0] - start[0]) * fraction
        lon = start[1] + (summit[1] - start[1]) * fraction

        # Elevation with smooth curve
        ele_fraction = math.sin(fraction * math.pi / 2)  # Smoother ascent
        ele = round(start_ele + gain * ele_fraction)

        path.append([round(lat, 5), round(lon, 5), ele])

    # Create chart
    chart = []
    for i in range(15):
        idx = int(i * (len(path) - 1) / 14)
        point_dist = (idx / (len(path) - 1)) * distance
        chart.append({
            "distance": round(point_dist, 2),
            "elevation": path[idx][2]
        })

    # Update trail
    trail['geo']['path'] = path
    trail['geo']['chart'] = chart

    # Update data_sources
    if 'data_sources' in data:
        data['data_sources']['gps_source'] = 'Generated from start/summit markers (pending GPX import)'
        if 'notes' in data['data_sources']:
            data['data_sources']['notes'] += ' GPS path generated from trail markers pending verified GPX import.'

    with open(trail_file, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"✅ Created path with {len(path)} points")
    print(f"   Density: {len(path) / distance:.1f} pts/mi")

    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 create-basic-path.py <trail-json>")
        sys.exit(1)

    create_path_from_markers(sys.argv[1])
