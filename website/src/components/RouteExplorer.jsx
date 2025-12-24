import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap } from 'react-leaflet';
import ElevationChart from './ElevationChart';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// --- ICONS (Same as before) ---
const createEmojiIcon = (emoji) => L.divIcon({
    className: 'custom-map-icon',
    html: `<div style="background-color: white; border: 2px solid rgba(0,0,0,0.1); border-radius: 50%; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; font-size: 18px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">${emoji}</div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -20]
});

const icons = {
    start: createEmojiIcon('🅿️'),
    summit: createEmojiIcon('⛰️'),
    waterfall: createEmojiIcon('💧'),
    hut: createEmojiIcon('🏠'),
    viewpoint: createEmojiIcon('🔭'),
    default: createEmojiIcon('📍')
};

// --- HELPER: Coordinate Sanitizer ---
const safeCoord = (lat, lon) => {
    const l = parseFloat(lat);
    const n = parseFloat(lon);
    if (isNaN(l) || isNaN(n)) return null;
    return [l, n];
};

// --- MAP HELPER: Bounds Fitter ---
function SetBounds({ bounds }) {
  const map = useMap();
  useEffect(() => {
    if (bounds && bounds.length > 0) {
        try { map.fitBounds(bounds, { padding: [50, 50] }); } catch(e) {}
    }
  }, [bounds, map]);
  return null;
}

// --- MAIN COMPONENT ---
// Notice the props: activeTrail and onTrailSelect come from Parent now
const RouteExplorer = ({ trails, lat, lon, activeTrail, onTrailSelect }) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const token = import.meta.env.PUBLIC_MAPBOX_TOKEN;

  // Fallback if activeTrail is null (Safety)
  if (!activeTrail) return null;

  // --- DATA SAFETY LAYER ---
  const defaultCenter = safeCoord(lat, lon) || [44.0, -71.0];
  const geo = activeTrail.geo || {};

  // Sanitize Path
  const rawPath = geo.path || [];
  const path = rawPath.map(p => safeCoord(p[0], p[1])).filter(p => p !== null);

  // Sanitize Markers
  const startRaw = geo.markers?.start || defaultCenter;
  const startPos = safeCoord(startRaw[0], startRaw[1]) || defaultCenter;
  const summitRaw = geo.markers?.summit || defaultCenter;
  const summitPos = safeCoord(summitRaw[0], summitRaw[1]) || defaultCenter;

  const features = (activeTrail.features || [])
    .map(f => ({ ...f, coords: safeCoord(f.lat, f.lon) }))
    .filter(f => f.coords !== null);

  const stats = activeTrail.stats || {};
  const parkingName = activeTrail.parking_info ? String(activeTrail.parking_info).split(',')[0] : "Trailhead Parking";

  return (
    <div className="w-full font-sans shadow-2xl rounded-3xl border border-stone-200 bg-white overflow-hidden">

        {/* --- MAP SECTION --- */}
        <div className="relative isolate group h-[500px] w-full bg-stone-100 z-0">
            <MapContainer
                key={activeTrail.name} // Keeps the map crash-proof
                center={startPos}
                zoom={13}
                scrollWheelZoom={false}
                style={{ height: "100%", width: "100%" }}
            >
                {token ? (
                    <TileLayer url={`https://api.mapbox.com/styles/v1/mapbox/outdoors-v12/tiles/{z}/{x}/{y}?access_token=${token}`} attribution='© Mapbox' tileSize={512} zoomOffset={-1} />
                ) : (
                    <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="OpenStreetMap" />
                )}

                {path.length > 0 && <SetBounds bounds={path} />}
                {path.length > 0 && <Polyline positions={path} pathOptions={{ color: '#059669', weight: 5, opacity: 0.9 }} />}

                <Marker position={startPos} icon={icons.start}><Popup>Trailhead</Popup></Marker>
                <Marker position={summitPos} icon={icons.summit}><Popup>Summit</Popup></Marker>

                {features.map((feature, idx) => (
                    <Marker key={idx} position={feature.coords} icon={icons.default}>
                        <Popup>{feature.name}</Popup>
                    </Marker>
                ))}
            </MapContainer>

            {/* ROUTE SELECTOR UI */}
            <div className="absolute bottom-6 left-4 z-[1000] max-w-xs w-[90%]">
                <div className="bg-white/90 backdrop-blur-md rounded-t-xl shadow-2xl border border-white/50 p-3 flex justify-between items-center cursor-pointer hover:bg-white transition"
                     onClick={() => setIsExpanded(!isExpanded)}>
                    <div className="flex items-center gap-3">
                        <div className="bg-emerald-600 text-white p-2 rounded-lg font-bold text-[10px] tracking-wide shadow-md shadow-emerald-200">
                            ROUTE
                        </div>
                        <div className="overflow-hidden">
                            <div className="text-[10px] font-bold uppercase text-stone-400 tracking-wider">Viewing</div>
                            <div className="font-bold text-stone-900 truncate pr-2 text-sm">{activeTrail.name}</div>
                        </div>
                    </div>
                    <button className="text-stone-400 p-1">{isExpanded ? "▼" : "▲"}</button>
                </div>

                {isExpanded && (
                    <div className="bg-white/90 backdrop-blur-md rounded-b-xl shadow-2xl border-x border-b border-white/50 overflow-hidden max-h-[300px] overflow-y-auto">
                        {trails.map((t, index) => (
                            <button
                                key={index}
                                // THIS IS THE FIX: We tell the Parent (Dashboard) to change the trail
                                onClick={() => onTrailSelect(t)}
                                className={`w-full text-left px-4 py-3 text-sm border-b border-stone-100/50 last:border-0 transition-colors flex justify-between items-center ${activeTrail.name === t.name ? 'bg-emerald-50/80' : 'hover:bg-white/50'}`}
                            >
                                <div className={`font-medium ${activeTrail.name === t.name ? 'text-emerald-900' : 'text-stone-700'}`}>{t.name}</div>
                                <span className={`text-[10px] font-bold px-2 py-1 rounded-full ${activeTrail.name === t.name ? 'bg-white text-emerald-700 shadow-sm' : 'bg-stone-100 text-stone-500'}`}>{t.stats?.distance || 0} mi</span>
                            </button>
                        ))}
                    </div>
                )}
            </div>
        </div>

        {/* --- LOGISTICS BAR --- */}
        <div className="bg-stone-50 border-t border-stone-200 p-6 grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="md:col-span-2 flex flex-col justify-between">
                <div>
                    <h3 className="text-sm font-bold uppercase tracking-wider text-stone-400 mb-2">Parking & Navigation</h3>
                    <div className="flex items-start gap-3">
                        <div className="text-2xl mt-1">🅿️</div>
                        <div>
                            <div className="font-bold text-stone-900 text-lg leading-tight mb-1">{parkingName}</div>
                            <p className="text-stone-500 text-sm">{activeTrail.parking_info || "Coordinates available below."}</p>
                        </div>
                    </div>
                </div>
                <div className="mt-4">
                    <a href={`http://googleusercontent.com/maps.google.com/?q=${startPos[0]},${startPos[1]}`} target="_blank" rel="noopener noreferrer" className="flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white py-3 rounded-xl font-bold text-sm transition shadow-lg shadow-emerald-100">
                        Navigate to Trailhead
                    </a>
                </div>
            </div>
        </div>

        {/* --- ELEVATION CHART --- */}
        {geo.chart && geo.chart.length > 0 && (
            <div className="border-t border-stone-200 p-6 bg-white w-full h-[350px]">
                <ElevationChart data={geo.chart} />
            </div>
        )}
    </div>
  );
};

export default RouteExplorer;