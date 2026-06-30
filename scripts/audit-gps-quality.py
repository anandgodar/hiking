#!/usr/bin/env python3
"""
Audit GPS data quality across all trail files

Checks:
- GPS points per mile (quality indicator)
- Elevation data completeness
- Path complexity (straight vs curved)
- Chart data accuracy
- Missing coordinates
"""

import json
import math
import os
from pathlib import Path

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

def calculate_path_distance(path):
    """Calculate total distance of GPS path"""
    if len(path) < 2:
        return 0

    total = 0
    for i in range(1, len(path)):
        total += haversine_distance(
            path[i-1][0], path[i-1][1],
            path[i][0], path[i][1]
        )
    return total

def audit_route(trail):
    """Score one route's GPS quality. Returns {score, issues, warnings, stats}."""
    GOOD_PPM = 15  # 15+ points per mile = good
    FAIR_PPM = 8   # 8-15 points per mile = fair

    rr = {'score': 100, 'issues': [], 'warnings': [], 'stats': {}}

    geo = trail.get('geo')
    if not geo:
        rr['issues'].append('No geo object')
        rr['score'] = 0
        return rr

    path = geo.get('path')
    if not path:
        rr['issues'].append('No GPS path data')
        rr['score'] = 0
        return rr

    num_points = len(path)
    stats = trail.get('stats', {})
    trail_distance = stats.get('distance', 0)
    if trail_distance == 0:
        trail_distance = calculate_path_distance(path)
        rr['warnings'].append(f'No distance in stats, calculated: {trail_distance:.1f} mi')

    if trail_distance > 0:
        points_per_mile = num_points / trail_distance
    else:
        points_per_mile = 0
        rr['warnings'].append('Trail distance is 0')

    if points_per_mile >= GOOD_PPM:
        gps_quality = 'GOOD'
    elif points_per_mile >= FAIR_PPM:
        gps_quality = 'FAIR'
        rr['warnings'].append(f'Low GPS density: {points_per_mile:.1f} pts/mi (recommend 15+)')
        rr['score'] -= 20
    else:
        gps_quality = 'POOR'
        rr['issues'].append(f'Very low GPS density: {points_per_mile:.1f} pts/mi (need 15+)')
        rr['score'] -= 40

    has_elevation = all(len(p) >= 3 for p in path)
    if not has_elevation:
        rr['issues'].append('Missing elevation data in path')
        rr['score'] -= 30

    chart = geo.get('chart') or []
    if not chart:
        rr['warnings'].append('No elevation chart data')
        rr['score'] -= 10
    elif len(chart) < 5:
        rr['warnings'].append(f'Too few chart points: {len(chart)} (recommend 10+)')
        rr['score'] -= 5

    if 'markers' not in geo:
        rr['warnings'].append('No start/summit markers')
        rr['score'] -= 5

    if num_points >= 3:
        straight_distance = haversine_distance(path[0][0], path[0][1],
                                               path[-1][0], path[-1][1])
        actual_distance = calculate_path_distance(path)
        if actual_distance > 0:
            straightness = straight_distance / actual_distance
            if straightness > 0.9:
                rr['warnings'].append(f'Path very straight: {straightness:.2f} (may be oversimplified)')
                rr['score'] -= 10

    rr['score'] = max(0, rr['score'])
    rr['stats'] = {
        'gps_points': num_points,
        'distance_mi': round(trail_distance, 1),
        'points_per_mile': round(points_per_mile, 1),
        'has_elevation': has_elevation,
        'chart_points': len(chart),
        'quality': gps_quality,
    }
    return rr


def audit_trail(file_path):
    """Audit a single trail file"""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)

        trail_name = data.get('name', 'Unknown')
        state = data.get('state', 'Unknown')

        results = {
            'name': trail_name,
            'state': state,
            'file': os.path.basename(file_path),
            'issues': [],
            'warnings': [],
            'quality_score': 100
        }

        # Check if trail has geo data
        if 'trails' not in data or len(data['trails']) == 0:
            results['issues'].append('No trails array found')
            results['quality_score'] = 0
            return results

        # Audit EVERY route, not just the first. A hiker can choose any route,
        # so the hike's score is gated by its weakest route.
        routes = data['trails']
        route_results = [audit_route(t) for t in routes]
        multi = len(routes) > 1

        results['quality_score'] = min(rr['score'] for rr in route_results)

        for idx, (trail, rr) in enumerate(zip(routes, route_results)):
            label = trail.get('name') or f'route {idx + 1}'
            prefix = f"[{label}] " if multi else ''
            for iss in rr['issues']:
                results['issues'].append(prefix + iss)
            for w in rr['warnings']:
                results['warnings'].append(prefix + w)

        # Representative stats = the weakest route (what the score reflects).
        worst = min(route_results, key=lambda r: r['score'])
        results['stats'] = dict(worst['stats'])
        results['stats']['routes_audited'] = len(routes)
        results['stats']['routes_below_80'] = sum(1 for rr in route_results if rr['score'] < 80)

        # Per-route breakdown for the report.
        results['routes'] = [
            {'name': (t.get('name') or f'route {i + 1}'), 'score': rr['score'],
             **rr['stats']}
            for i, (t, rr) in enumerate(zip(routes, route_results))
        ]

        return results

    except json.JSONDecodeError:
        return {
            'name': 'Parse Error',
            'file': os.path.basename(file_path),
            'issues': ['Invalid JSON'],
            'quality_score': 0
        }
    except Exception as e:
        return {
            'name': 'Error',
            'file': os.path.basename(file_path),
            'issues': [f'Error: {str(e)}'],
            'quality_score': 0
        }

def audit_all_trails(data_dir='/home/user/hiking/website/src/data'):
    """Audit all trail files"""
    all_results = []

    # Find all JSON files
    for state_dir in Path(data_dir).iterdir():
        if state_dir.is_dir():
            for trail_file in state_dir.glob('*.json'):
                result = audit_trail(trail_file)
                result['state_slug'] = state_dir.name
                all_results.append(result)

    return all_results

def print_report(results):
    """Print formatted audit report"""
    # Sort by quality score
    results.sort(key=lambda x: x.get('quality_score', 0))

    print("=" * 80)
    print("GPS DATA QUALITY AUDIT REPORT")
    print("=" * 80)
    print()

    # Summary stats
    total_trails = len(results)
    good_trails = sum(1 for r in results if r.get('quality_score', 0) >= 80)
    fair_trails = sum(1 for r in results if 50 <= r.get('quality_score', 0) < 80)
    poor_trails = sum(1 for r in results if r.get('quality_score', 0) < 50)

    print(f"Total trails analyzed: {total_trails}")
    print(f"  GOOD (80-100): {good_trails} trails")
    print(f"  FAIR (50-79):  {fair_trails} trails")
    print(f"  POOR (<50):    {poor_trails} trails")
    print()

    # Trails needing fixes (quality < 80)
    needs_fix = [r for r in results if r.get('quality_score', 0) < 80]

    if needs_fix:
        print("=" * 80)
        print("TRAILS NEEDING GPS DATA FIXES")
        print("=" * 80)
        print()

        for result in needs_fix:
            score = result.get('quality_score', 0)
            stats = result.get('stats', {})

            print(f"📍 {result['name']} ({result['state']})")
            print(f"   File: {result['file']}")
            print(f"   Quality Score: {score}/100")

            if stats:
                print(f"   GPS Points: {stats.get('gps_points', 0)} " +
                      f"({stats.get('points_per_mile', 0)} pts/mi)")
                print(f"   Distance: {stats.get('distance_mi', 0)} mi")
                print(f"   Quality: {stats.get('quality', 'UNKNOWN')}")

            if result.get('issues'):
                print(f"   ❌ Issues:")
                for issue in result['issues']:
                    print(f"      - {issue}")

            if result.get('warnings'):
                print(f"   ⚠️  Warnings:")
                for warning in result['warnings']:
                    print(f"      - {warning}")

            print()

    # Top priority fixes
    critical = [r for r in results if r.get('quality_score', 0) < 50]

    if critical:
        print("=" * 80)
        print("🔴 CRITICAL: HIGHEST PRIORITY FIXES")
        print("=" * 80)
        print()

        for result in critical[:10]:  # Top 10
            stats = result.get('stats', {})
            print(f"{result['name']:40} " +
                  f"{stats.get('points_per_mile', 0):5.1f} pts/mi " +
                  f"(score: {result.get('quality_score', 0)}/100)")

        print()

    # Export JSON report
    output_file = '/home/user/hiking/gps-audit-report.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n📄 Full report exported to: {output_file}")
    print()

if __name__ == "__main__":
    print("🔍 Auditing GPS data quality across all trails...\n")
    results = audit_all_trails()
    print_report(results)
