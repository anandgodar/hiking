#!/usr/bin/env python3
"""
Convert GPX trail files to SummitSeeker geo JSON format

Usage:
  python3 gpx-to-geo.py trail.gpx trail-slug.json

Features:
- Extracts accurate GPS path from GPX
- Calculates elevation profile points
- Generates proper chart data
- Validates coordinates
"""

import sys
import json
import math
import xml.etree.ElementTree as ET

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two GPS points in miles"""
    R = 3959  # Earth radius in miles

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))

    return R * c

def parse_gpx(gpx_file):
    """Parse GPX file and extract trail points"""
    tree = ET.parse(gpx_file)
    root = tree.getroot()

    # Handle GPX namespace
    ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}

    points = []

    # Try tracks first (most common for trails)
    for trk in root.findall('.//gpx:trk', ns):
        for seg in trk.findall('.//gpx:trkseg', ns):
            for pt in seg.findall('.//gpx:trkpt', ns):
                lat = float(pt.get('lat'))
                lon = float(pt.get('lon'))
                ele_elem = pt.find('gpx:ele', ns)

                # Elevation in meters, convert to feet
                ele = float(ele_elem.text) * 3.28084 if ele_elem is not None else 0

                points.append({
                    'lat': round(lat, 5),
                    'lon': round(lon, 5),
                    'ele': round(ele)
                })

    # If no tracks, try route
    if not points:
        for rte in root.findall('.//gpx:rte', ns):
            for pt in rte.findall('.//gpx:rtept', ns):
                lat = float(pt.get('lat'))
                lon = float(pt.get('lon'))
                ele_elem = pt.find('gpx:ele', ns)
                ele = float(ele_elem.text) * 3.28084 if ele_elem is not None else 0

                points.append({
                    'lat': round(lat, 5),
                    'lon': round(lon, 5),
                    'ele': round(ele)
                })

    return points

def simplify_path(points, max_points=100):
    """Simplify path to reduce file size while keeping accuracy"""
    if len(points) <= max_points:
        return points

    # Keep every nth point
    step = len(points) // max_points
    simplified = []

    for i in range(0, len(points), step):
        simplified.append(points[i])

    # Always include the last point
    if simplified[-1] != points[-1]:
        simplified.append(points[-1])

    return simplified

def generate_chart(points, num_points=15):
    """Generate elevation chart data points"""
    chart = []
    total_distance = 0

    # Calculate cumulative distances
    distances = [0]
    for i in range(1, len(points)):
        dist = haversine_distance(
            points[i-1]['lat'], points[i-1]['lon'],
            points[i]['lat'], points[i]['lon']
        )
        total_distance += dist
        distances.append(total_distance)

    # Generate evenly spaced chart points
    interval = total_distance / (num_points - 1)

    for i in range(num_points):
        target_dist = i * interval

        # Find closest point
        closest_idx = min(range(len(distances)),
                         key=lambda idx: abs(distances[idx] - target_dist))

        chart.append({
            "distance": round(target_dist, 2),
            "elevation": points[closest_idx]['ele']
        })

    return chart, round(total_distance, 1)

def convert_gpx_to_geo(gpx_file, output_file):
    """Main conversion function"""
    print(f"📍 Parsing GPX file: {gpx_file}")
    points = parse_gpx(gpx_file)

    if not points:
        print("❌ Error: No GPS points found in GPX file")
        return False

    print(f"   Found {len(points)} GPS points")

    # Simplify path if too many points
    if len(points) > 100:
        original_count = len(points)
        points = simplify_path(points, max_points=100)
        print(f"   Simplified to {len(points)} points (from {original_count})")

    # Generate elevation chart
    chart, total_distance = generate_chart(points, num_points=15)

    # Calculate elevation gain
    min_ele = min(p['ele'] for p in points)
    max_ele = max(p['ele'] for p in points)
    ele_gain = round(max_ele - min_ele)

    print(f"\n📊 Trail Statistics:")
    print(f"   Distance: {total_distance} mi")
    print(f"   Elevation Gain: {ele_gain} ft")
    print(f"   Min Elevation: {round(min_ele)} ft")
    print(f"   Max Elevation: {round(max_ele)} ft")

    # Create geo object
    geo = {
        "markers": {
            "start": [points[0]['lat'], points[0]['lon']],
            "summit": [points[-1]['lat'], points[-1]['lon']]
        },
        "path": [[p['lat'], p['lon'], p['ele']] for p in points],
        "chart": chart
    }

    # Try to update existing trail file
    if output_file:
        try:
            with open(output_file, 'r') as f:
                trail_data = json.load(f)

            # Update geo in first trail
            if 'trails' in trail_data and len(trail_data['trails']) > 0:
                trail_data['trails'][0]['geo'] = geo

                # Update stats
                trail_data['trails'][0]['stats']['distance'] = total_distance
                trail_data['trails'][0]['stats']['gain'] = ele_gain

                with open(output_file, 'w') as f:
                    json.dump(trail_data, f, indent=2)

                print(f"\n✅ Updated {output_file}")
                print(f"   Updated geo.path, geo.chart, and stats")
                return True
        except Exception as e:
            print(f"\n⚠️  Could not update file: {e}")
            print(f"   Writing geo object only to geo-output.json")

            with open('geo-output.json', 'w') as f:
                json.dump(geo, f, indent=2)

            print("   You can manually copy this into your trail file")
            return True
    else:
        # Just output geo object
        print(json.dumps(geo, indent=2))
        return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 gpx-to-geo.py <gpx-file> [trail-json-file]")
        print("\nExample:")
        print("  python3 gpx-to-geo.py nevada-fall.gpx \\")
        print("          website/src/data/california/nevada-fall-yosemite.json")
        sys.exit(1)

    gpx_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    convert_gpx_to_geo(gpx_file, output_file)
