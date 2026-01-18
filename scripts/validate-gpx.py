#!/usr/bin/env python3
"""
Validate GPX files before conversion

Checks:
- Valid GPX format
- Has track or route data
- Has elevation data
- Reasonable distance
- GPS point density
"""

import sys
import xml.etree.ElementTree as ET
import math

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

def validate_gpx(gpx_file):
    """Validate a GPX file"""
    print(f"Validating: {gpx_file}")
    print("=" * 60)

    try:
        tree = ET.parse(gpx_file)
        root = tree.getroot()

        # Check namespace
        ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}

        # Try old GPX 1.0 namespace
        if not root.findall('.//gpx:trk', ns):
            ns = {'gpx': 'http://www.topografix.com/GPX/1/0'}

        print("✅ Valid XML format")

        # Count points
        points = []

        # Check tracks
        for trk in root.findall('.//gpx:trk', ns):
            for seg in trk.findall('.//gpx:trkseg', ns):
                for pt in seg.findall('.//gpx:trkpt', ns):
                    lat = float(pt.get('lat'))
                    lon = float(pt.get('lon'))
                    ele_elem = pt.find('gpx:ele', ns)
                    ele = float(ele_elem.text) if ele_elem is not None else None

                    points.append({'lat': lat, 'lon': lon, 'ele': ele})

        # Check routes if no tracks
        if not points:
            for rte in root.findall('.//gpx:rte', ns):
                for pt in rte.findall('.//gpx:rtept', ns):
                    lat = float(pt.get('lat'))
                    lon = float(pt.get('lon'))
                    ele_elem = pt.find('gpx:ele', ns)
                    ele = float(ele_elem.text) if ele_elem is not None else None

                    points.append({'lat': lat, 'lon': lon, 'ele': ele})

        if not points:
            print("❌ No GPS points found (no tracks or routes)")
            return False

        print(f"✅ Found {len(points)} GPS points")

        # Check elevation data
        has_elevation = sum(1 for p in points if p['ele'] is not None)
        elevation_percent = (has_elevation / len(points)) * 100

        if elevation_percent >= 95:
            print(f"✅ Has elevation data ({has_elevation}/{len(points)} points = {elevation_percent:.0f}%)")
        elif elevation_percent >= 50:
            print(f"⚠️  Partial elevation data ({has_elevation}/{len(points)} points = {elevation_percent:.0f}%)")
        else:
            print(f"❌ Missing elevation data ({has_elevation}/{len(points)} points = {elevation_percent:.0f}%)")

        # Calculate distance
        total_distance = 0
        for i in range(1, len(points)):
            dist = haversine_distance(
                points[i-1]['lat'], points[i-1]['lon'],
                points[i]['lat'], points[i]['lon']
            )
            total_distance += dist

        print(f"📏 Trail distance: {total_distance:.1f} miles")

        # Check GPS density
        if total_distance > 0:
            points_per_mile = len(points) / total_distance

            if points_per_mile >= 50:
                quality = "EXCELLENT"
                emoji = "🌟"
            elif points_per_mile >= 15:
                quality = "GOOD"
                emoji = "✅"
            elif points_per_mile >= 8:
                quality = "FAIR"
                emoji = "⚠️ "
            else:
                quality = "POOR"
                emoji = "❌"

            print(f"{emoji} GPS density: {points_per_mile:.1f} points/mile ({quality})")

            if quality in ["GOOD", "EXCELLENT"]:
                print("")
                print("=" * 60)
                print("✅ GPX FILE IS READY FOR CONVERSION")
                print("=" * 60)
                print("")
                print(f"This GPX will produce {quality} quality trail data.")
                print("")
                return True
            elif quality == "FAIR":
                print("")
                print("=" * 60)
                print("⚠️  GPX FILE IS USABLE BUT NOT IDEAL")
                print("=" * 60)
                print("")
                print("This GPX will work, but consider finding a more detailed version.")
                print("")
                return True
            else:
                print("")
                print("=" * 60)
                print("❌ GPX FILE QUALITY TOO LOW")
                print("=" * 60)
                print("")
                print("This GPX is too simplified. Please find a more detailed version.")
                print(f"Recommended: 15+ points/mile, Current: {points_per_mile:.1f} points/mile")
                print("")
                return False
        else:
            print("❌ Cannot calculate distance (points too close)")
            return False

    except ET.ParseError as e:
        print(f"❌ Invalid XML: {e}")
        return False
    except Exception as e:
        print(f"❌ Validation error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 validate-gpx.py <gpx-file>")
        print("")
        print("Example:")
        print("  python3 validate-gpx.py gpx-downloads/nevada-fall.gpx")
        sys.exit(1)

    gpx_file = sys.argv[1]
    success = validate_gpx(gpx_file)

    sys.exit(0 if success else 1)
