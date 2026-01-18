#!/usr/bin/env python3
"""Fix JSON syntax errors in California trail files"""

import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "website/src/data/california"

files_to_fix = [
    "cathedral-lakes-yosemite.json",
    "lower-yosemite-fall.json",
    "may-lake-yosemite.json",
    "mirror-lake-yosemite.json",
    "nevada-fall-yosemite.json",
    "panorama-trail-yosemite.json",
    "sentinel-dome-taft-point.json",
    "upper-yosemite-fall.json",
]

for filename in files_to_fix:
    filepath = DATA_DIR / filename

    if not filepath.exists():
        print(f"❌ File not found: {filename}")
        continue

    content = filepath.read_text()

    # Fix pattern: remove extra closing brace and blank lines between seo and data_sources
    # Pattern: "seo": { ... }\n  },\n\n  "data_sources"
    # Should be: "seo": { ... }\n  },\n\n  "data_sources"

    # Remove duplicate closing braces after seo block
    content = re.sub(
        r'("seo": \{[^}]+\})\n  \},\n+  \},',
        r'\1\n  },',
        content,
        flags=re.DOTALL | re.MULTILINE
    )

    # Remove extra blank lines and fix structure
    content = re.sub(
        r'("seo": \{[^}]+\})\n+  \},\n+\n+  ("data_sources")',
        r'\1\n  },\n\n  \2',
        content,
        flags=re.DOTALL | re.MULTILINE
    )

    # Fix any trailing issues before final closing brace
    content = re.sub(
        r'("notes": "[^"]+"\n  \})\n+\n+\}',
        r'\1\n}',
        content
    )

    # Write back
    filepath.write_text(content)

    # Validate JSON
    try:
        with open(filepath) as f:
            json.load(f)
        print(f"✅ Fixed: {filename}")
    except json.JSONDecodeError as e:
        print(f"❌ Still broken: {filename} - {e}")

print("\nDone!")
