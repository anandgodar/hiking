import React, { useMemo, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

/**
 * Explore Map — every published trail on one national map.
 * CircleMarkers on a canvas renderer (fast at 800+ points), colored by
 * difficulty with a fixed legend; one filter row (difficulty + state) per
 * the site's interaction pattern. Each dot pops a card linking to the guide.
 */

const DIFF_COLORS = {
  Easy: '#059669',       // emerald — matches the site's Easy badge
  Moderate: '#d97706',   // amber
  Hard: '#dc2626',       // red (Hard + Strenuous share the "serious" hue)
  Strenuous: '#7c2d12',  // deep brown-red, darker step of the same family
};
const DIFF_ORDER = ['Easy', 'Moderate', 'Hard', 'Strenuous'];

const ExploreMap = ({ trails }) => {
  const [diff, setDiff] = useState('All');
  const [state, setState] = useState('All');

  const states = useMemo(
    () => [...new Set(trails.map(t => t.state).filter(Boolean))].sort(),
    [trails]
  );

  const visible = useMemo(
    () => trails.filter(t =>
      (diff === 'All' || t.difficulty === diff) &&
      (state === 'All' || t.state === state)),
    [trails, diff, state]
  );

  const token = import.meta.env.PUBLIC_MAPBOX_TOKEN;

  return (
    <div>
      {/* Filter row */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        {['All', ...DIFF_ORDER].map(d => (
          <button
            key={d}
            onClick={() => setDiff(d)}
            className={`px-3 py-1.5 rounded-full text-sm font-semibold border transition-colors ${
              diff === d
                ? 'bg-stone-900 text-white border-stone-900'
                : 'bg-white text-stone-700 border-stone-300 hover:border-stone-500'
            }`}
          >
            {d !== 'All' && (
              <span className="inline-block w-2.5 h-2.5 rounded-full mr-1.5 align-middle"
                    style={{ background: DIFF_COLORS[d] }} />
            )}
            {d}
          </button>
        ))}
        <select
          value={state}
          onChange={e => setState(e.target.value)}
          className="ml-auto px-3 py-1.5 rounded-lg border border-stone-300 text-sm bg-white text-stone-700"
          aria-label="Filter by state"
        >
          <option value="All">All states</option>
          {states.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <span className="text-sm text-stone-500 font-medium">{visible.length} trails</span>
      </div>

      <div className="rounded-2xl overflow-hidden border border-stone-200 shadow-sm">
        <MapContainer
          center={[39.8, -98.5]}
          zoom={4}
          minZoom={3}
          style={{ height: '70vh', width: '100%' }}
          preferCanvas={true}
          scrollWheelZoom={true}
        >
          {token ? (
            <TileLayer
              url={`https://api.mapbox.com/styles/v1/mapbox/outdoors-v12/tiles/{z}/{x}/{y}?access_token=${token}`}
              attribution="© Mapbox © OpenStreetMap"
              tileSize={512}
              zoomOffset={-1}
            />
          ) : (
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution="© OpenStreetMap contributors"
            />
          )}

          {visible.map(t => (
            <CircleMarker
              key={t.slug}
              center={[t.lat, t.lon]}
              radius={5}
              pathOptions={{
                color: '#ffffff',
                weight: 1.5,
                fillColor: DIFF_COLORS[t.difficulty] || '#57534e',
                fillOpacity: 0.9,
              }}
            >
              <Popup>
                <div style={{ minWidth: 180 }}>
                  <a href={`/${t.state_slug}/hikes/${t.slug}`}
                     style={{ fontWeight: 700, color: '#047857', fontSize: 15 }}>
                    {t.name}
                  </a>
                  <div style={{ fontSize: 12, color: '#57534e', marginTop: 4 }}>
                    {t.state} · {t.elevation ? t.elevation.toLocaleString() + ' ft' : ''}
                    {t.distance ? ` · ${t.distance} mi` : ''}
                    {t.difficulty ? ` · ${t.difficulty}` : ''}
                  </div>
                  <a href={`/${t.state_slug}/hikes/${t.slug}`}
                     style={{ fontSize: 12, color: '#047857', fontWeight: 600 }}>
                    View trail guide →
                  </a>
                </div>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>

      {/* Legend (always present) */}
      <div className="flex flex-wrap gap-4 mt-3 text-sm text-stone-600">
        {DIFF_ORDER.map(d => (
          <span key={d} className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full border border-white shadow-sm"
                  style={{ background: DIFF_COLORS[d] }} />
            {d}
          </span>
        ))}
      </div>
    </div>
  );
};

export default ExploreMap;
