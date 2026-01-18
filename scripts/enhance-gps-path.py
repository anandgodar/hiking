#!/usr/bin/env python3
"""
Enhance existing GPS paths with interpolation and elevation data

This creates better GPS paths when actual GPX files aren't available.
Uses intelligent interpolation between existing points plus elevation modeling.
"""

import json
import math
import sys

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two GPS points in miles"""
    R = 3959
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))

    return R * c

def interpolate_points(start, end, num_points, start_ele, end_ele):
    """Interpolate points between start and end with elevation"""
    points = []

    for i in range(num_points + 1):
        fraction = i / num_points

        # Linear interpolation for lat/lon
        lat = start[0] + (end[0] - start[0]) * fraction
        lon = start[1] + (end[1] - start[1]) * fraction

        # Elevation with some variation (sinusoidal to simulate terrain)
        base_ele = start_ele + (end_ele - start_ele) * fraction

        # Add terrain variation (small ups and downs)
        variation = math.sin(fraction * math.pi * 3) * 50  # ±50 ft variation

        ele = round(base_ele + variation)

        points.append([round(lat, 5), round(lon, 5), ele])

    return points

def enhance_trail_gps(trail_file, target_points_per_mile=20):
    """Enhance a trail's GPS data"""

    print(f"Enhancing: {trail_file}")
    print("=" * 60)

    with open(trail_file, 'r') as f:
        data = json.load(f)

    trail_name = data.get('name', 'Unknown')
    print(f"Trail: {trail_name}")

    if 'trails' not in data or len(data['trails']) == 0:
        print("❌ No trails data found")
        return False

    trail = data['trails'][0]

    if 'geo' not in trail or 'path' not in trail['geo']:
        print("❌ No existing GPS path")
        return False

    existing_path = trail['geo']['path']
    stats = trail.get('stats', {})
    trail_distance = stats.get('distance', 0)

    if trail_distance == 0:
        # Calculate from existing path
        trail_distance = sum(
            haversine_distance(
                existing_path[i][0], existing_path[i][1],
                existing_path[i+1][0], existing_path[i+1][1]
            )
            for i in range(len(existing_path) - 1)
        )

    print(f"Distance: {trail_distance:.1f} mi")
    print(f"Existing points: {len(existing_path)}")

    # Calculate target number of points
    target_points = int(trail_distance * target_points_per_mile)
    print(f"Target points: {target_points} ({target_points_per_mile} pts/mi)")

    # Get elevation gain from stats
    elevation_gain = stats.get('gain', 2000)

    # Calculate elevations for existing points
    if len(existing_path[0]) < 3:
        # No elevation data, need to add it
        start_markers = trail['geo'].get('markers', {})
        start_coords = start_markers.get('start', existing_path[0][:2])

        # Estimate starting elevation (Yosemite Valley ~4000ft)
        start_ele = 4000

        if 'valley' in trail_name.lower() or 'bridalveil' in trail_name.lower():
            start_ele = 4000
        elif 'whitney' in trail_name.lower():
            start_ele = 8300
        elif 'mission' in trail_name.lower():
            start_ele = 200

        end_ele = start_ele + elevation_gain

        # Add elevation to existing points (linear distribution)
        for i, point in enumerate(existing_path):
            fraction = i / (len(existing_path) - 1) if len(existing_path) > 1 else 0
            ele = round(start_ele + elevation_gain * fraction)

            if len(point) == 2:
                existing_path[i] = [point[0], point[1], ele]
            elif len(point) >= 3:
                existing_path[i] = [point[0], point[1], point[2]]

    # Now interpolate between existing points
    enhanced_path = []

    for i in range(len(existing_path) - 1):
        start = existing_path[i]
        end = existing_path[i + 1]

        # Calculate segment distance
        segment_dist = haversine_distance(start[0], start[1], end[0], end[1])

        # Number of points to add in this segment
        # Use ceiling to ensure we get enough points
        # For very short trails, ensure minimum 15 points per segment
        desired_points = int(math.ceil(segment_dist * target_points_per_mile))
        segment_points = max(15, desired_points)

        # Interpolate
        interpolated = interpolate_points(
            start[:2], end[:2],
            segment_points,
            start[2], end[2]
        )

        # Add all but the last point (to avoid duplicates)
        enhanced_path.extend(interpolated[:-1])

    # Add the final point
    enhanced_path.append(existing_path[-1])

    print(f"Enhanced points: {len(enhanced_path)}")
    print(f"New density: {len(enhanced_path) / trail_distance:.1f} pts/mi")

    # Generate elevation chart (15 evenly spaced points)
    chart_points = 15
    chart = []
    total_distance = 0
    distances = [0]

    # Calculate cumulative distances
    for i in range(1, len(enhanced_path)):
        dist = haversine_distance(
            enhanced_path[i-1][0], enhanced_path[i-1][1],
            enhanced_path[i][0], enhanced_path[i][1]
        )
        total_distance += dist
        distances.append(total_distance)

    # Generate chart points
    for i in range(chart_points):
        target_dist = (i / (chart_points - 1)) * total_distance

        # Find closest point
        closest_idx = min(range(len(distances)),
                         key=lambda idx: abs(distances[idx] - target_dist))

        chart.append({
            "distance": round(target_dist, 2),
            "elevation": enhanced_path[closest_idx][2]
        })

    # Update trail data
    trail['geo']['path'] = enhanced_path
    trail['geo']['chart'] = chart

    # Update markers
    trail['geo']['markers'] = {
        "start": enhanced_path[0][:2],
        "summit": enhanced_path[-1][:2]
    }

    # Update data_sources to note this is enhanced data
    if 'data_sources' in data:
        data['data_sources']['gps_source'] = 'Enhanced via interpolation (pending GPX import)'
        data['data_sources']['notes'] += ' GPS path enhanced with interpolated points and estimated elevation data pending verified GPX import.'

    # Save
    with open(trail_file, 'w') as f:
        json.dump(data, f, indent=2)

    print("✅ Enhanced successfully")
    print()

    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 enhance-gps-path.py <trail-json-file>")
        print("")
        print("Example:")
        print("  python3 enhance-gps-path.py website/src/data/california/nevada-fall-yosemite.json")
        sys.exit(1)

    trail_file = sys.argv[1]
    enhance_trail_gps(trail_file)
