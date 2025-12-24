import React from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix for default marker icons
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

let DefaultIcon = L.icon({
    iconUrl: icon,
    shadowUrl: iconShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41]
});
L.Marker.prototype.options.icon = DefaultIcon;

export default function TrailMap({ lat, lon, name }) {
  // Mock Path (Triangle) - We will replace this with real GPX later
  const trailPath = data.gpx_path;

  return (
    <div className="h-80 w-full rounded-3xl overflow-hidden border border-white/20 shadow-2xl relative group">

       <MapContainer
          center={[lat, lon]}
          zoom={14}
          scrollWheelZoom={false}
          zoomControl={false} // Hides the ugly +/- buttons for a clean look
          style={{ height: "100%", width: "100%" }}
       >
        {/* 1. SATELLITE LAYER (Much clearer for mountains) */}
        <TileLayer
          attribution='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        />

        {/* 2. HYBRID LABELS (Road names overlaid on top) */}
        <TileLayer
          url="https://stamen-tiles-{s}.a.ssl.fastly.net/toner-hybrid/{z}/{x}/{y}{r}.png"
          opacity={0.5}
        />

        <Marker position={[lat, lon]}>
          <Popup className="text-xs font-bold">{name} Summit</Popup>
        </Marker>

        {/* 3. NEON TRAIL LINE (High Contrast) */}
        <Polyline
            positions={trailPath}
            pathOptions={{
                color: '#39ff14', // Neon Green
                weight: 5,
                opacity: 0.9,
                lineCap: 'round'
            }}
        />
      </MapContainer>

      {/* Custom Overlay UI */}
      <div className="absolute top-4 left-4 bg-black/40 backdrop-blur-md px-3 py-1 rounded-full border border-white/10 z-[1000] pointer-events-none">
        <span className="text-[10px] font-bold text-white uppercase tracking-widest">Satellite View</span>
      </div>

      <div className="absolute bottom-0 left-0 w-full h-12 bg-gradient-to-t from-black/80 to-transparent z-[1000] pointer-events-none"></div>
    </div>
  );
}