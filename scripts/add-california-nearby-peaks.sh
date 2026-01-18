#!/bin/bash

# Add nearby_peaks to key California trails

cd "$(dirname "$0")/../website/src/data/california"

# Clouds Rest - add Half Dome and Cathedral Lakes
sed -i '/^  "page_content": {$/i\
  "nearby_peaks": [\
    {\
      "name": "Half Dome",\
      "slug": "half-dome-yosemite",\
      "state_slug": "california",\
      "elevation": 8842,\
      "distance_miles": 6.2\
    },\
    {\
      "name": "Cathedral Lakes",\
      "slug": "cathedral-lakes-yosemite",\
      "state_slug": "california",\
      "elevation": 9585,\
      "distance_miles": 5.4\
    },\
    {\
      "name": "Sentinel Dome",\
      "slug": "sentinel-dome-taft-point",\
      "state_slug": "california",\
      "elevation": 8122,\
      "distance_miles": 7.1\
    }\
  ],\
' clouds-rest-yosemite.json

# Mist Trail (Vernal Fall) - add other waterfalls and Half Dome
sed -i '/^  "page_content": {$/i\
  "nearby_peaks": [\
    {\
      "name": "Nevada Fall",\
      "slug": "nevada-fall-yosemite",\
      "state_slug": "california",\
      "elevation": 5900,\
      "distance_miles": 1.5\
    },\
    {\
      "name": "Half Dome",\
      "slug": "half-dome-yosemite",\
      "state_slug": "california",\
      "elevation": 8842,\
      "distance_miles": 3.5\
    },\
    {\
      "name": "Upper Yosemite Fall",\
      "slug": "upper-yosemite-fall",\
      "state_slug": "california",\
      "elevation": 6500,\
      "distance_miles": 4.2\
    }\
  ],\
' mist-trail-vernal-fall.json

# Sentinel Dome - add other Glacier Point area trails
sed -i '/^  "page_content": {$/i\
  "nearby_peaks": [\
    {\
      "name": "Half Dome",\
      "slug": "half-dome-yosemite",\
      "state_slug": "california",\
      "elevation": 8842,\
      "distance_miles": 4.8\
    },\
    {\
      "name": "Clouds Rest",\
      "slug": "clouds-rest-yosemite",\
      "state_slug": "california",\
      "elevation": 9926,\
      "distance_miles": 7.1\
    }\
  ],\
' sentinel-dome-taft-point.json

# Cathedral Lakes - add other High Sierra trails
sed -i '/^  "page_content": {$/i\
  "nearby_peaks": [\
    {\
      "name": "Clouds Rest",\
      "slug": "clouds-rest-yosemite",\
      "state_slug": "california",\
      "elevation": 9926,\
      "distance_miles": 5.4\
    },\
    {\
      "name": "Half Dome",\
      "slug": "half-dome-yosemite",\
      "state_slug": "california",\
      "elevation": 8842,\
      "distance_miles": 9.5\
    },\
    {\
      "name": "May Lake",\
      "slug": "may-lake-yosemite",\
      "state_slug": "california",\
      "elevation": 9329,\
      "distance_miles": 6.8\
    }\
  ],\
' cathedral-lakes-yosemite.json

echo "✅ Added nearby_peaks to 4 more California trails!"
