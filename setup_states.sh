#!/bin/bash

# 1. Create the modular directory
echo "📂 Creating directory structure..."
mkdir -p data_pipeline/seeds

# 2. Create the Registry (__init__.py)
# This file dynamically finds and loads every state module you are about to create.
echo "🧠 Generating Registry (__init__.py)..."
cat > data_pipeline/seeds/__init__.py << 'EOF'
import pkgutil
import importlib

def load_all_mountains():
    """
    Dynamically imports every module in the 'seeds' folder
    and aggregates their get_mountains() data.
    """
    all_mountains = []
    package_path = __path__
    package_name = __name__

    print(f"📂 Scanning for State Modules in {package_path}...")

    for _, module_name, _ in pkgutil.iter_modules(package_path):
        try:
            module = importlib.import_module(f"{package_name}.{module_name}")
            if hasattr(module, 'get_mountains'):
                mountains = module.get_mountains()
                if mountains:
                    print(f"   found: {module_name} ({len(mountains)} peaks)")
                    all_mountains.extend(mountains)
        except Exception as e:
            print(f"   ⚠️ Error loading {module_name}: {e}")

    print(f"✅ Total Registry: {len(all_mountains)} mountains loaded.\n")
    return all_mountains
EOF

# 3. Define the list of all US States (Slug | Name)
# We use a simple pipe-delimited format for the loop
states=(
"al|Alabama" "ak|Alaska" "az|Arizona" "ar|Arkansas" "ca|California"
"co|Colorado" "ct|Connecticut" "de|Delaware" "dc|District of Columbia"
"fl|Florida" "ga|Georgia" "hi|Hawaii" "id|Idaho" "il|Illinois"
"in|Indiana" "ia|Iowa" "ks|Kansas" "ky|Kentucky" "la|Louisiana"
"me|Maine" "md|Maryland" "ma|Massachusetts" "mi|Michigan" "mn|Minnesota"
"ms|Mississippi" "mo|Missouri" "mt|Montana" "ne|Nebraska" "nv|Nevada"
"nh|New Hampshire" "nj|New Jersey" "nm|New Mexico" "ny|New York"
"nc|North Carolina" "nd|North Dakota" "oh|Ohio" "ok|Oklahoma"
"or|Oregon" "pa|Pennsylvania" "ri|Rhode Island" "sc|South Carolina"
"sd|South Dakota" "tn|Tennessee" "tx|Texas" "ut|Utah" "vt|Vermont"
"va|Virginia" "wa|Washington" "wv|West Virginia" "wi|Wisconsin" "wy|Wyoming"
)

# 4. Loop through and create each file
echo "🇺🇸 Generating 51 State Modules..."

for item in "${states[@]}"; do
    slug="${item%%|*}"
    name="${item##*|}"
    filename="data_pipeline/seeds/usa_${slug}.py"

    # Only create if it doesn't exist (to prevent overwriting your work later)
    if [ ! -f "$filename" ]; then
        cat > "$filename" << EOF
def get_mountains():
    return [
        # --- ${name} MOUNTAINS ---
        # Copy/Paste this block for each mountain
        # {
        #     "name": "Example Peak",
        #     "slug": "example-peak-${slug}",
        #     "state": "${name}",
        #     "state_slug": "${slug}",
        #     "elevation": 0,
        #     "lat": 0.0000, "lon": 0.0000,
        #     "trails_config": [
        #         {
        #             "name": "Standard Route",
        #             "type": "Out & Back",
        #             "difficulty": "Moderate",
        #             "distance_miles": 0.0,
        #             "start_lat": 0.0000, "start_lon": 0.0000
        #         }
        #     ]
        # }
    ]
EOF
        echo "   + Created: usa_${slug}.py"
    else
        echo "   . Skipped: usa_${slug}.py (already exists)"
    fi
done

echo "✅ Architecture Complete."
echo "👉 Next Step: Open 'data_pipeline/seeds/usa_nh.py' and paste your NH data there."