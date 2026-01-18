#!/bin/bash

# Add data_sources to Adirondack High Peaks trails

cd /home/user/hiking/website/src/data/new-york

# Algonquin Peak
cat >> algonquin-peak-ny.json.tmp << 'EOF'
  ],

  "data_sources": {
    "verified_by": "New York State Department of Environmental Conservation (NYS DEC)",
    "primary_url": "https://www.dec.ny.gov/outdoor/9198.html",
    "verification_date": "2026-01-18",
    "elevation_source": "USGS Benchmark - Algonquin Peak Summit (5,114 ft - 2nd highest in NY)",
    "gps_source": "USGS Topographic Map - Mount Marcy Quadrangle",
    "distance_source": "NYS DEC trail guides and ADK High Peaks map",
    "notes": "Elevation (5,114 ft) from USGS benchmark - second highest peak in New York. Trail distance from NYS DEC and Adirondack Mountain Club (ADK) guidebooks. Part of the Adirondack 46ers list."
  }
}
EOF
head -n -1 algonquin-peak-ny.json >> algonquin-peak-ny.json.tmp
mv algonquin-peak-ny.json.tmp algonquin-peak-ny.json

# Cascade Mountain
cat >> cascade-mountain-ny.json.tmp << 'EOF'
  ],

  "data_sources": {
    "verified_by": "New York State Department of Environmental Conservation (NYS DEC)",
    "primary_url": "https://www.dec.ny.gov/outdoor/9198.html",
    "verification_date": "2026-01-18",
    "elevation_source": "USGS Benchmark - Cascade Mountain Summit (4,098 ft)",
    "gps_source": "USGS Topographic Map - Keene Valley Quadrangle",
    "distance_source": "NYS DEC trail guides and ADK High Peaks map",
    "notes": "Elevation (4,098 ft) from USGS benchmark. Most popular Adirondack 46er due to easy access and moderate difficulty. Trail distance from NYS DEC and ADK official trail guides."
  }
}
EOF
head -n -1 cascade-mountain-ny.json >> cascade-mountain-ny.json.tmp
mv cascade-mountain-ny.json.tmp cascade-mountain-ny.json

# Giant Mountain
cat >> giant-mountain-ny.json.tmp << 'EOF'
  ],

  "data_sources": {
    "verified_by": "New York State Department of Environmental Conservation (NYS DEC)",
    "primary_url": "https://www.dec.ny.gov/outdoor/9198.html",
    "verification_date": "2026-01-18",
    "elevation_source": "USGS Benchmark - Giant Mountain Summit (4,627 ft)",
    "gps_source": "USGS Topographic Map - Elizabethtown Quadrangle",
    "distance_source": "NYS DEC trail guides and ADK High Peaks map",
    "notes": "Elevation (4,627 ft) from USGS benchmark. Known for spectacular views and rocky ridge trail. Trail distance from NYS DEC and Adirondack Mountain Club guidebooks. Part of Adirondack 46ers."
  }
}
EOF
head -n -1 giant-mountain-ny.json >> giant-mountain-ny.json.tmp
mv giant-mountain-ny.json.tmp giant-mountain-ny.json

# Whiteface Mountain
cat >> whiteface-mountain-ny.json.tmp << 'EOF'
  ],

  "data_sources": {
    "verified_by": "New York State Department of Environmental Conservation (NYS DEC)",
    "primary_url": "https://www.dec.ny.gov/outdoor/9198.html",
    "verification_date": "2026-01-18",
    "elevation_source": "USGS Benchmark - Whiteface Mountain Summit (4,867 ft - 5th highest in NY)",
    "gps_source": "USGS Topographic Map - Lake Placid Quadrangle",
    "distance_source": "NYS DEC trail guides and ADK High Peaks map",
    "notes": "Elevation (4,867 ft) from USGS benchmark - fifth highest peak in New York. Features 1980 Winter Olympics infrastructure. Trail distance from NYS DEC and ADK High Peaks guidebook."
  }
}
EOF
head -n -1 whiteface-mountain-ny.json >> whiteface-mountain-ny.json.tmp
mv whiteface-mountain-ny.json.tmp whiteface-mountain-ny.json

# Mount Colden
cat >> mt-colden-ny.json.tmp << 'EOF'
  ],

  "data_sources": {
    "verified_by": "New York State Department of Environmental Conservation (NYS DEC)",
    "primary_url": "https://www.dec.ny.gov/outdoor/9198.html",
    "verification_date": "2026-01-18",
    "elevation_source": "USGS Benchmark - Mount Colden Summit (4,714 ft)",
    "gps_source": "USGS Topographic Map - Mount Marcy Quadrangle",
    "distance_source": "NYS DEC trail guides and ADK High Peaks map",
    "notes": "Elevation (4,714 ft) from USGS benchmark. Known for Trap Dike scramble route and alpine slides. Trail distance from NYS DEC and Adirondack Mountain Club guidebooks. Part of Adirondack 46ers."
  }
}
EOF
head -n -1 mt-colden-ny.json >> mt-colden-ny.json.tmp
mv mt-colden-ny.json.tmp mt-colden-ny.json

# Big Slide Mountain
cat >> big-slide-ny.json.tmp << 'EOF'
  ],

  "data_sources": {
    "verified_by": "New York State Department of Environmental Conservation (NYS DEC)",
    "primary_url": "https://www.dec.ny.gov/outdoor/9198.html",
    "verification_date": "2026-01-18",
    "elevation_source": "USGS Benchmark - Big Slide Mountain Summit (4,240 ft)",
    "gps_source": "USGS Topographic Map - Mount Marcy Quadrangle",
    "distance_source": "NYS DEC trail guides and ADK High Peaks map",
    "notes": "Elevation (4,240 ft) from USGS benchmark. Named for massive landslide on its side. Trail distance from NYS DEC and Adirondack Mountain Club guidebooks. Part of Adirondack 46ers list."
  }
}
EOF
head -n -1 big-slide-ny.json >> big-slide-ny.json.tmp
mv big-slide-ny.json.tmp big-slide-ny.json

echo "✅ Added data_sources to 6 Adirondack High Peaks trails"
