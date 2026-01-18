import React, { useEffect, useState, useMemo } from 'react';
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap } from 'react-leaflet';
import ElevationChart from './ElevationChart';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// --- ICONS ---
const createEmojiIcon = (emoji, size = 32) => L.divIcon({
    className: 'custom-map-icon',
    html: `<div style="background-color: white; border: 2px solid rgba(0,0,0,0.15); border-radius: 50%; width: ${size}px; height: ${size}px; display: flex; align-items: center; justify-content: center; font-size: ${size * 0.56}px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);">${emoji}</div>`,
    iconSize: [size, size],
    iconAnchor: [size/2, size/2],
    popupAnchor: [0, -size/2]
});

const createLabelIcon = (emoji, label, color = '#059669') => L.divIcon({
    className: 'custom-label-icon',
    html: `
        <div style="display: flex; flex-direction: column; align-items: center; transform: translateX(-50%);">
            <div style="background-color: white; border: 2px solid ${color}; border-radius: 50%; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; font-size: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.2);">${emoji}</div>
            <div style="background: ${color}; color: white; font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 4px; margin-top: 4px; white-space: nowrap; box-shadow: 0 1px 3px rgba(0,0,0,0.2);">${label}</div>
        </div>
    `,
    iconSize: [80, 60],
    iconAnchor: [40, 20],
    popupAnchor: [0, -20]
});

// Feature type to icon mapping
const featureIcons = {
    waterfall: '💧',
    falls: '💧',
    cascade: '💧',
    pond: '🏊',
    lake: '🏊',
    water: '💦',
    viewpoint: '👁️',
    overlook: '👁️',
    summit: '⛰️',
    peak: '⛰️',
    shelter: '🏠',
    hut: '🏠',
    lean_to: '🏕️',
    campsite: '⛺',
    junction: '🔀',
    bridge: '🌉',
    spring: '💧',
    scramble: '🧗',
    ladder: '🪜',
    fire_tower: '🗼',
    tower: '🗼',
    landmark: '📍',
    boardwalk: '🚶',
    parking: '🅿️',
    trailhead: '🥾',
    restaurant: '🍽️',
    swimming: '🏊',
    picnic: '🧺',
    default: '📍'
};

const getFeatureIcon = (type) => {
    const iconType = type?.toLowerCase() || 'default';
    return featureIcons[iconType] || featureIcons.default;
};

// --- HELPER: Coordinate Sanitizer ---
const safeCoord = (lat, lon) => {
    const l = parseFloat(lat);
    const n = parseFloat(lon);
    if (isNaN(l) || isNaN(n) || l < -90 || l > 90 || n < -180 || n > 180) return null;
    return [l, n];
};

// --- HELPER: Create curved path from straight line ---
const createCurvedPath = (start, end, numPoints = 20, isLoop = false) => {
    if (!start || !end) return [];

    const [startLat, startLon] = start;
    const [endLat, endLon] = end;

    // Calculate direction and distance
    const dx = endLon - startLon;
    const dy = endLat - startLat;
    const dist = Math.sqrt(dx*dx + dy*dy);

    if (dist === 0) return [start, end];

    // Normalize perpendicular vector (for lateral offset)
    const perpX = -dy / dist;
    const perpY = dx / dist;

    const points = [];

    if (isLoop) {
        // Create a teardrop/lollipop loop shape
        // Start at parking, go to summit via one side, return via other side
        for (let i = 0; i <= numPoints; i++) {
            const t = i / numPoints;

            let lat, lon;

            if (t <= 0.5) {
                // First half: go OUT to summit (right side of loop)
                const progress = t * 2; // 0 to 1
                lat = startLat + dy * progress;
                lon = startLon + dx * progress;

                // Bulge to the right
                const bulge = Math.sin(progress * Math.PI) * dist * 0.3;
                lat += perpX * bulge;
                lon += perpY * bulge;
            } else {
                // Second half: come BACK from summit (left side of loop)
                const progress = (1 - t) * 2; // 1 to 0
                lat = startLat + dy * progress;
                lon = startLon + dx * progress;

                // Bulge to the left
                const bulge = Math.sin(progress * Math.PI) * dist * 0.3;
                lat -= perpX * bulge;
                lon -= perpY * bulge;
            }

            points.push([lat, lon]);
        }

        // Close the loop by returning to start
        points.push([startLat, startLon]);

    } else {
        // Out & Back: Create natural winding path with switchbacks
        for (let i = 0; i <= numPoints; i++) {
            const t = i / numPoints;

            // Base position (linear interpolation)
            let lat = startLat + dy * t;
            let lon = startLon + dx * t;

            // Add natural winding (stronger in middle, zero at ends)
            if (t > 0.02 && t < 0.98) {
                // Smooth curve envelope (0 at ends, max in middle)
                const envelope = Math.sin(t * Math.PI);

                // Multiple sine waves for natural switchback feel
                const wave1 = Math.sin(t * Math.PI * 3) * 0.3;
                const wave2 = Math.sin(t * Math.PI * 5 + 0.5) * 0.15;
                const combined = (wave1 + wave2) * envelope;

                // Scale offset based on trail length
                const scale = Math.min(dist * 0.12, 0.006);

                lat += perpX * combined * scale * 60;
                lon += perpY * combined * scale * 60;
            }

            points.push([lat, lon]);
        }
    }

    return points;
};

// --- MAP HELPER: Bounds Fitter ---
function SetBounds({ bounds, trailDistance }) {
    const map = useMap();
    useEffect(() => {
        if (bounds && bounds.length >= 2) {
            try {
                // For very short trails, use higher zoom
                const maxZoom = trailDistance < 1 ? 16 : trailDistance < 3 ? 15 : 14;
                map.fitBounds(bounds, {
                    padding: [80, 80],
                    maxZoom: maxZoom
                });
            } catch(e) {
                console.warn('Failed to fit bounds:', e);
            }
        }
    }, [bounds, map, trailDistance]);
    return null;
}

// --- QUICK STATS COMPONENT ---
const QuickStats = ({ stats }) => (
    <div className="bg-white rounded-xl border border-stone-200 p-4">
        <h4 className="text-xs font-bold uppercase tracking-wider text-stone-400 mb-3">Quick Stats</h4>
        <div className="space-y-2">
            <div className="flex justify-between">
                <span className="text-stone-500 text-sm">Distance</span>
                <span className="font-semibold text-stone-900">{stats?.distance || '—'} mi</span>
            </div>
            <div className="flex justify-between">
                <span className="text-stone-500 text-sm">Elevation Gain</span>
                <span className="font-semibold text-stone-900">{stats?.gain?.toLocaleString() || '—'} ft</span>
            </div>
            <div className="flex justify-between">
                <span className="text-stone-500 text-sm">Difficulty</span>
                <span className="font-semibold text-stone-900">{stats?.difficulty || '—'}</span>
            </div>
        </div>
    </div>
);

// --- MAIN COMPONENT ---
const RouteExplorer = ({ trails, lat, lon, activeTrail, onTrailSelect }) => {
    const [isExpanded, setIsExpanded] = useState(false);
    const token = import.meta.env.PUBLIC_MAPBOX_TOKEN;

    // Fallback if activeTrail is null
    if (!activeTrail) return null;

    // --- EXTRACT DATA ---
    const summitCoord = safeCoord(lat, lon);
    const defaultCenter = summitCoord || [44.0, -71.0];

    const geo = activeTrail.geo || {};
    const stats = activeTrail.stats || {};

    // Get start position - check multiple sources
    let startPos = null;

    // 1. From geo.markers.start
    if (geo.markers?.start && Array.isArray(geo.markers.start) && geo.markers.start.length >= 2) {
        startPos = safeCoord(geo.markers.start[0], geo.markers.start[1]);
    }

    // 2. From activeTrail.start_lat/start_lon
    if (!startPos && activeTrail.start_lat && activeTrail.start_lon) {
        startPos = safeCoord(activeTrail.start_lat, activeTrail.start_lon);
    }

    // 3. From logistics.start_coords
    if (!startPos && activeTrail.logistics?.start_coords) {
        const coords = activeTrail.logistics.start_coords;
        if (Array.isArray(coords) && coords.length >= 2) {
            startPos = safeCoord(coords[0], coords[1]);
        }
    }

    // 4. Estimate from summit
    if (!startPos && summitCoord) {
        const distMiles = activeTrail.distance_miles || stats?.distance || 2;
        const offset = Math.min(distMiles * 0.005, 0.03);
        startPos = [summitCoord[0] - offset, summitCoord[1] + offset * 0.5];
    }

    // Final fallback
    if (!startPos) {
        startPos = defaultCenter;
    }

    // Get summit position
    let summitPos = summitCoord;
    if (geo.markers?.summit && Array.isArray(geo.markers.summit) && geo.markers.summit.length >= 2) {
        summitPos = safeCoord(geo.markers.summit[0], geo.markers.summit[1]) || summitCoord;
    }

    // --- PATH HANDLING ---
    const rawPath = geo.path || [];
    let path = rawPath
        .map(p => {
            if (Array.isArray(p) && p.length >= 2) {
                return safeCoord(p[0], p[1]);
            }
            return null;
        })
        .filter(p => p !== null);

    // Check if this is a loop trail
    const trailType = activeTrail.type?.toLowerCase() || '';
    const isLoop = trailType.includes('loop');

    const trailDistance = activeTrail.distance_miles || stats?.distance || 2;

    // Only generate curved path if backend didn't provide one
    // Backend should always provide good paths now
    const hasValidBackendPath = path.length >= 10;

    if (!hasValidBackendPath && startPos && summitPos) {
        // Fallback: generate path only if backend failed
        const numPoints = Math.max(20, Math.min(40, Math.floor(trailDistance * 8)));
        path = createCurvedPath(startPos, summitPos, numPoints, isLoop);
    }

    // Ensure path endpoints match markers
    if (path.length >= 2 && startPos && summitPos) {
        // Verify first/last points are close to start/summit
        const firstDist = Math.abs(path[0][0] - startPos[0]) + Math.abs(path[0][1] - startPos[1]);
        const lastDist = Math.abs(path[path.length-1][0] - summitPos[0]) + Math.abs(path[path.length-1][1] - summitPos[1]);

        // Only adjust if significantly off (> 0.01 degrees ~ 0.7 miles)
        if (firstDist > 0.01) {
            path[0] = startPos;
        }
        if (lastDist > 0.01 && !isLoop) {
            path[path.length - 1] = summitPos;
        }
    }

    // For loops, ensure path closes back to start
    if (isLoop && path.length >= 2) {
        const firstPoint = path[0];
        const lastPoint = path[path.length - 1];
        if (firstPoint && lastPoint) {
            const closeDistance = Math.abs(firstPoint[0] - lastPoint[0]) + Math.abs(firstPoint[1] - lastPoint[1]);
            if (closeDistance > 0.0001) {
                path.push([...firstPoint]);
            }
        }
    }

    // --- FEATURES ---
    const features = useMemo(() => {
        const rawFeatures = activeTrail.features || [];
        return rawFeatures
            .map(f => ({
                ...f,
                coords: safeCoord(f.lat, f.lon),
                icon: getFeatureIcon(f.type)
            }))
            .filter(f => f.coords !== null);
    }, [activeTrail.features]);

    // --- BOUNDS ---
    const bounds = useMemo(() => {
        const allPoints = [...path];
        if (startPos) allPoints.push(startPos);
        if (summitPos) allPoints.push(summitPos);
        features.forEach(f => {
            if (f.coords) allPoints.push(f.coords);
        });
        return allPoints.filter(p => p !== null);
    }, [path, startPos, summitPos, features]);

    // Parking info
    const parkingName = activeTrail.parking_info
        ? String(activeTrail.parking_info).split(',')[0].trim()
        : "Trailhead Parking";
    const parkingDetails = activeTrail.parking_details || {};
    const parkingFee = parkingDetails.fee || 'Check locally';

    return (
        <div className="w-full font-sans shadow-2xl rounded-3xl border border-stone-200 bg-white overflow-hidden">

            {/* --- MAP SECTION --- */}
            <div className="relative isolate group h-[450px] w-full bg-stone-100 z-0">
                <MapContainer
                    key={`${activeTrail.name}-${path.length}`}
                    center={startPos || defaultCenter}
                    zoom={13}
                    scrollWheelZoom={false}
                    style={{ height: "100%", width: "100%" }}
                >
                    {token ? (
                        <TileLayer
                            url={`https://api.mapbox.com/styles/v1/mapbox/outdoors-v12/tiles/{z}/{x}/{y}?access_token=${token}`}
                            attribution='© Mapbox'
                            tileSize={512}
                            zoomOffset={-1}
                        />
                    ) : (
                        <TileLayer
                            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                            attribution="© OpenStreetMap"
                        />
                    )}

                    {bounds.length >= 2 && <SetBounds bounds={bounds} trailDistance={trailDistance} />}

                    {/* Trail Path */}
                    {path.length >= 2 && (
                        <>
                            {/* Shadow/outline */}
                            <Polyline
                                positions={path}
                                pathOptions={{
                                    color: '#064e3b',
                                    weight: 7,
                                    opacity: 0.3,
                                    lineCap: 'round',
                                    lineJoin: 'round'
                                }}
                            />
                            {/* Main line */}
                            <Polyline
                                positions={path}
                                pathOptions={{
                                    color: '#059669',
                                    weight: 4,
                                    opacity: 0.9,
                                    lineCap: 'round',
                                    lineJoin: 'round'
                                }}
                            />
                        </>
                    )}

                    {/* Parking/Trailhead Marker */}
                    {startPos && (
                        <Marker
                            position={startPos}
                            icon={createLabelIcon('🅿️', 'Parking', '#3b82f6')}
                            zIndexOffset={1000}
                        >
                            <Popup>
                                <div className="font-semibold">{parkingName}</div>
                                <div className="text-sm text-gray-600">Fee: {parkingFee}</div>
                            </Popup>
                        </Marker>
                    )}

                    {/* Summit/Destination Marker */}
                    {summitPos && (
                        <Marker
                            position={summitPos}
                            icon={createLabelIcon(
                                activeTrail.tags?.includes('Waterfall') ? '💧' : '⛰️',
                                activeTrail.tags?.includes('Waterfall') ? 'Falls' : 'Summit',
                                '#dc2626'
                            )}
                            zIndexOffset={1000}
                        >
                            <Popup>
                                <div className="font-semibold">
                                    {activeTrail.tags?.includes('Waterfall') ? 'Waterfall' : 'Summit / Destination'}
                                </div>
                                <div className="text-sm text-gray-600">{lat?.toFixed(4)}, {lon?.toFixed(4)}</div>
                            </Popup>
                        </Marker>
                    )}

                    {/* Feature Markers */}
                    {features.map((feature, idx) => (
                        <Marker
                            key={`feature-${idx}-${feature.name}`}
                            position={feature.coords}
                            icon={createEmojiIcon(feature.icon, 28)}
                            zIndexOffset={500}
                        >
                            <Popup>
                                <div className="font-semibold">{feature.name}</div>
                                {feature.mile && (
                                    <div className="text-sm text-gray-600">Mile {feature.mile}</div>
                                )}
                                {feature.type && (
                                    <div className="text-xs text-gray-400 capitalize">{feature.type}</div>
                                )}
                            </Popup>
                        </Marker>
                    ))}
                </MapContainer>

                {/* ROUTE SELECTOR UI */}
                <div className="absolute bottom-4 left-4 z-[1000] max-w-xs w-[280px]">
                    <div
                        className="bg-white/95 backdrop-blur-md rounded-xl shadow-xl border border-stone-200 overflow-hidden"
                    >
                        <div
                            className="p-3 flex justify-between items-center cursor-pointer hover:bg-stone-50 transition"
                            onClick={() => setIsExpanded(!isExpanded)}
                        >
                            <div className="flex items-center gap-3">
                                <div className="bg-emerald-600 text-white px-2 py-1 rounded-lg font-bold text-[10px] tracking-wide">
                                    ROUTE
                                </div>
                                <div className="overflow-hidden">
                                    <div className="text-[10px] font-medium text-stone-400 uppercase tracking-wider">Viewing</div>
                                    <div className="font-semibold text-stone-800 truncate text-sm">{activeTrail.name}</div>
                                </div>
                            </div>
                            <button className="text-stone-400 p-1 hover:text-stone-600 transition">
                                {isExpanded ? "▲" : "▼"}
                            </button>
                        </div>

                        {isExpanded && trails.length > 1 && (
                            <div className="border-t border-stone-100 max-h-[200px] overflow-y-auto">
                                {trails.map((t, index) => (
                                    <button
                                        key={index}
                                        onClick={() => {
                                            onTrailSelect(t);
                                            setIsExpanded(false);
                                        }}
                                        className={`w-full text-left px-4 py-2.5 text-sm border-b border-stone-50 last:border-0 transition-colors flex justify-between items-center ${
                                            activeTrail.name === t.name 
                                                ? 'bg-emerald-50 text-emerald-900' 
                                                : 'hover:bg-stone-50 text-stone-700'
                                        }`}
                                    >
                                        <span className="font-medium truncate pr-2">{t.name}</span>
                                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0 ${
                                            activeTrail.name === t.name 
                                                ? 'bg-emerald-100 text-emerald-700' 
                                                : 'bg-stone-100 text-stone-500'
                                        }`}>
                                            {t.stats?.distance || t.distance_miles || '—'} mi
                                        </span>
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {/* Features Legend (if features exist) */}
                {features.length > 0 && (
                    <div className="absolute top-4 right-4 z-[1000] bg-white/95 backdrop-blur-md rounded-lg shadow-lg border border-stone-200 p-2 max-w-[180px]">
                        <div className="text-[10px] font-bold text-stone-400 uppercase tracking-wider mb-1.5 px-1">
                            Trail Features
                        </div>
                        <div className="space-y-1">
                            {features.slice(0, 5).map((f, idx) => (
                                <div key={idx} className="flex items-center gap-2 text-xs text-stone-600 px-1 py-0.5 hover:bg-stone-50 rounded">
                                    <span>{f.icon}</span>
                                    <span className="truncate">{f.name}</span>
                                </div>
                            ))}
                            {features.length > 5 && (
                                <div className="text-[10px] text-stone-400 px-1">
                                    +{features.length - 5} more
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>

            {/* --- LOGISTICS BAR --- */}
            <div className="bg-stone-50 border-t border-stone-200 p-5 grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="md:col-span-2">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-stone-400 mb-3">
                        Parking & Navigation
                    </h3>
                    <div className="flex items-start gap-3">
                        <div className="text-2xl bg-blue-100 p-2 rounded-lg">🅿️</div>
                        <div className="flex-1">
                            <div className="font-bold text-stone-900 text-base mb-0.5">{parkingName}</div>
                            <p className="text-stone-500 text-sm mb-1">
                                {activeTrail.parking_info || `${startPos?.[0]?.toFixed(4)}, ${startPos?.[1]?.toFixed(4)}`}
                            </p>
                            <div className="text-xs text-stone-400">
                                Fee: {parkingFee}
                            </div>
                        </div>
                    </div>
                    <div className="mt-4">
                        <a
                            href={`https://www.google.com/maps/dir/?api=1&destination=${startPos?.[0]},${startPos?.[1]}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white py-3 rounded-xl font-semibold text-sm transition shadow-lg shadow-emerald-600/20"
                        >
                            <span>🧭</span>
                            Navigate to Trailhead
                        </a>
                    </div>
                </div>
                <QuickStats stats={stats} />
            </div>

            {/* --- ELEVATION CHART --- */}
            {geo.chart && geo.chart.length > 0 && (
                <div className="border-t border-stone-200 p-5 bg-white">
                    <div className="h-[280px]">
                        <ElevationChart data={geo.chart} />
                    </div>
                </div>
            )}
        </div>
    );
};

export default RouteExplorer;