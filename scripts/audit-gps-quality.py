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

        trail = data['trails'][0]

        # Check for geo object
        if 'geo' not in trail:
            results['issues'].append('No geo object')
            results['quality_score'] = 0
            return results

        geo = trail['geo']

        # Check for path
        if 'path' not in geo or len(geo['path']) == 0:
            results['issues'].append('No GPS path data')
            results['quality_score'] = 0
            return results

        path = geo['path']
        num_points = len(path)

        # Get trail stats
        stats = trail.get('stats', {})
        trail_distance = stats.get('distance', 0)

        if trail_distance == 0:
            # Calculate from path
            trail_distance = calculate_path_distance(path)
            results['warnings'].append(f'No distance in stats, calculated: {trail_distance:.1f} mi')

        # Calculate GPS points per mile
        if trail_distance > 0:
            points_per_mile = num_points / trail_distance
        else:
            points_per_mile = 0
            results['warnings'].append('Trail distance is 0')

        # Quality thresholds
        GOOD_PPM = 15  # 15+ points per mile = good
        FAIR_PPM = 8   # 8-15 points per mile = fair
        # < 8 points per mile = poor

        # Assess GPS quality
        if points_per_mile >= GOOD_PPM:
            gps_quality = 'GOOD'
        elif points_per_mile >= FAIR_PPM:
            gps_quality = 'FAIR'
            results['warnings'].append(f'Low GPS density: {points_per_mile:.1f} pts/mi (recommend 15+)')
            results['quality_score'] -= 20
        else:
            gps_quality = 'POOR'
            results['issues'].append(f'Very low GPS density: {points_per_mile:.1f} pts/mi (need 15+)')
            results['quality_score'] -= 40

        # Check elevation data
        has_elevation = all(len(p) >= 3 for p in path)
        if not has_elevation:
            results['issues'].append('Missing elevation data in path')
            results['quality_score'] -= 30

        # Check for elevation chart
        if 'chart' not in geo or len(geo['chart']) == 0:
            results['warnings'].append('No elevation chart data')
            results['quality_score'] -= 10
        else:
            chart_points = len(geo['chart'])
            if chart_points < 5:
                results['warnings'].append(f'Too few chart points: {chart_points} (recommend 10+)')
                results['quality_score'] -= 5

        # Check markers
        if 'markers' not in geo:
            results['warnings'].append('No start/summit markers')
            results['quality_score'] -= 5

        # Calculate path straightness (detect oversimplified paths)
        if num_points >= 3:
            straight_distance = haversine_distance(
                path[0][0], path[0][1],
                path[-1][0], path[-1][1]
            )
            actual_distance = calculate_path_distance(path)

            if actual_distance > 0:
                straightness = straight_distance / actual_distance

                # Most trails should be < 0.8 straight (switchbacks, curves)
                if straightness > 0.9:
                    results['warnings'].append(f'Path very straight: {straightness:.2f} (may be oversimplified)')
                    results['quality_score'] -= 10

        # Add summary stats
        results['stats'] = {
            'gps_points': num_points,
            'distance_mi': round(trail_distance, 1),
            'points_per_mile': round(points_per_mile, 1),
            'has_elevation': has_elevation,
            'chart_points': len(geo.get('chart', [])),
            'quality': gps_quality
        }

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
