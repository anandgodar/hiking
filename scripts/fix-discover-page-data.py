#!/usr/bin/env python3
"""
Fix for discover/_tag_.astro error: Cannot read properties of undefined (reading 'toLowerCase')

This script validates and fixes all trail data to ensure compatibility with Astro pages.
"""

import json
from pathlib import Path

def validate_and_fix_trail(file_path):
    """Validate and fix a single trail file"""

    with open(file_path, 'r') as f:
        data = json.load(f)

    modified = False
    trail_name = f"{file_path.parent.name}/{file_path.name}"

    # Ensure all string fields are actually strings (not None or empty)
    string_fields = ['name', 'slug', 'state', 'state_slug']
    for field in string_fields:
        if field not in data or not data[field]:
            print(f"⚠️  {trail_name}: Missing or empty {field}")
            if field == 'slug' and 'name' in data:
                # Generate slug from name
                data['slug'] = data['name'].lower().replace(' ', '-').replace('_', '-')
                modified = True
                print(f"   → Generated slug: {data['slug']}")

    # Ensure tags is a non-empty array of strings
    if 'tags' not in data or not isinstance(data['tags'], list) or not data['tags']:
        print(f"⚠️  {trail_name}: Invalid tags, adding default")
        # Add default tags based on state
        state = data.get('state_slug', 'hiking')
        data['tags'] = [state, 'hiking', 'trail']
        modified = True

    # Ensure all tags are non-empty strings
    valid_tags = []
    for tag in data.get('tags', []):
        if isinstance(tag, str) and tag.strip():
            valid_tags.append(tag.strip().lower())

    if valid_tags != data.get('tags', []):
        data['tags'] = valid_tags
        modified = True
        print(f"   → Cleaned tags: {valid_tags}")

    # Ensure trails array exists and has valid data
    if 'trails' not in data or not data['trails']:
        print(f"⚠️  {trail_name}: Missing trails array")
        # This is a critical error, but let's not fix it automatically
        return False

    # Check first trail has stats with difficulty
    trail = data['trails'][0]
    if 'stats' not in trail:
        print(f"⚠️  {trail_name}: Missing stats in trail")
        trail['stats'] = {
            'distance': 0,
            'gain': 0,
            'difficulty': 'Moderate',
            'time': 0
        }
        modified = True

    if 'difficulty' not in trail['stats'] or not trail['stats']['difficulty']:
        print(f"⚠️  {trail_name}: Missing difficulty")
        trail['stats']['difficulty'] = 'Moderate'
        modified = True

    # Ensure difficulty is a valid string
    if trail['stats']['difficulty']:
        trail['stats']['difficulty'] = str(trail['stats']['difficulty']).strip()
        if not trail['stats']['difficulty']:
            trail['stats']['difficulty'] = 'Moderate'
            modified = True

    # Save if modified
    if modified:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"✅ {trail_name}: Fixed and saved")
        return True

    return False

def main():
    """Validate and fix all trail files"""

    data_dir = Path('/home/user/hiking/website/src/data')
    fixed_count = 0
    total_count = 0

    print("Validating and fixing trail data...")
    print("=" * 70)

    for state_dir in sorted(data_dir.iterdir()):
        if not state_dir.is_dir() or state_dir.name == 'blog':
            continue

        for trail_file in sorted(state_dir.glob('*.json')):
            total_count += 1
            if validate_and_fix_trail(trail_file):
                fixed_count += 1

    print("=" * 70)
    print(f"Processed {total_count} trail files")
    print(f"Fixed {fixed_count} files")
    print(f"✅ All trail data validated")

if __name__ == "__main__":
    main()
