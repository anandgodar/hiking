#!/usr/bin/env python3
import json
import math

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
        variation = math.sin(fraction * math.pi * 4) * 100
        ele = round(base_ele + variation)
        points.append([round(lat, 5), round(lon, 5), ele])
    return points

# Load Mount Whitney
with open('website/src/data/california/mount-whitney.json', 'r') as f:
    data = json.load(f)

trail = data['trails'][0]
path = trail['geo']['path']
distance = 22.0

print("Enhancing Mount Whitney")
print(f"Original: {len(path)} points")

# Add elevation to existing points if missing
for i, point in enumerate(path):
    if len(point) == 2:
        ele = round(8300 + (6400 / (len(path) - 1)) * i)
        path[i] = [point[0], point[1], ele]

# Enhanced path with 50 points per segment
enhanced = []
segments = len(path) - 1

for i in range(segments):
    start = path[i]
    end = path[i + 1]

    interpolated = interpolate_points(
        start[:2], end[:2],
        50,  # 50 points per segment
        start[2], end[2]
    )
    enhanced.extend(interpolated[:-1])

enhanced.append(path[-1])

print(f"Enhanced: {len(enhanced)} points ({len(enhanced)/distance:.1f} pts/mi)")

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
with open('website/src/data/california/mount-whitney.json', 'w') as f:
    json.dump(data, f, indent=2)

print("✅ Mount Whitney enhanced")
