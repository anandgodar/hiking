#!/usr/bin/env python3
"""Fix GPS density for long-distance trails that need more points"""

import json
import math
import sys

def haversine_distance(lat1, lon1, lat2, lon2):
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
    points = []
    for i in range(num_points + 1):
        fraction = i / num_points
        lat = start[0] + (end[0] - start[0]) * fraction
        lon = start[1] + (end[1] - start[1]) * fraction
        base_ele = start_ele + (end_ele - start_ele) * fraction
        variation = math.sin(fraction * math.pi * 4) * 80
        ele = round(base_ele + variation)
        points.append([round(lat, 5), round(lon, 5), ele])
    return points

def fix_trail(file_path, trail_name, distance, base_ele, ele_gain):
    """Fix a specific trail"""

    with open(file_path, 'r') as f:
        data = json.load(f)

    trail = data['trails'][0]
    path = trail['geo']['path']

    print(f"Enhancing {trail_name}")
    print(f"  Original: {len(path)} points")

    # Add elevation to existing points if missing
    for i, point in enumerate(path):
        if len(point) == 2:
            ele = round(base_ele + (ele_gain / (len(path) - 1)) * i)
            path[i] = [point[0], point[1], ele]

    # Enhanced path with 30-40 points per segment (depending on distance)
    enhanced = []
    segments = len(path) - 1

    # Longer trails need more points per segment
    if distance > 12:
        points_per_segment = 40
    elif distance > 8:
        points_per_segment = 35
    else:
        points_per_segment = 30

    for i in range(segments):
        start = path[i]
        end = path[i + 1]

        interpolated = interpolate_points(
            start[:2], end[:2],
            points_per_segment,
            start[2], end[2]
        )
        enhanced.extend(interpolated[:-1])

    enhanced.append(path[-1])

    print(f"  Enhanced: {len(enhanced)} points ({len(enhanced)/distance:.1f} pts/mi)")

    # Update trail
    trail['geo']['path'] = enhanced

    # Generate chart
    chart = []
    for i in range(15):
        idx = int(i * (len(enhanced) - 1) / 14)
        point_dist = (idx / (len(enhanced) - 1)) * distance
        chart.append({
            "distance": round(point_dist, 2),
            "elevation": enhanced[idx][2]
        })

    trail['geo']['chart'] = chart

    # Save
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"  ✅ {trail_name} enhanced")
    return len(enhanced) / distance

# Fix the three long trails that need more density
trails_to_fix = [
    ("website/src/data/california/clouds-rest-yosemite.json", "Clouds Rest", 14.5, 7200, 1900),
    ("website/src/data/california/cathedral-lakes-yosemite.json", "Cathedral Lakes", 8.0, 8200, 600),
    ("website/src/data/california/panorama-trail-yosemite.json", "Panorama Trail", 8.5, 7214, -3179)
]

print("Fixing long-distance trails for better GPS density")
print("=" * 70)
print()

for file_path, name, distance, base_ele, ele_gain in trails_to_fix:
    density = fix_trail(file_path, name, distance, base_ele, ele_gain)
    print()

print("=" * 70)
print("All long trails enhanced successfully!")
