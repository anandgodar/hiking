import React from 'react';

/**
 * Nearby Peaks Component (React version)
 * FIXED: URL now includes /hikes/ path segment
 */

// Helper to normalize state slug
const normalizeState = (s) => {
  if (s === 'nh') return 'new-hampshire';
  if (s === 'me') return 'maine';
  if (s === 'vt') return 'vermont';
  if (s === 'ny') return 'new-york';
  return s || 'new-hampshire';
};

const NearbyPeaks = ({ peaks }) => {
  if (!peaks || peaks.length === 0) return null;

  return (
    <div className="bg-white rounded-2xl p-6 border border-stone-200 shadow-sm mt-6">
      <h3 className="font-serif text-lg font-bold text-stone-900 mb-4 border-b border-stone-100 pb-2">
        Nearby Peaks
      </h3>
      <div className="space-y-3">
        {peaks.map((peak) => (
          // FIXED: Added /hikes/ to URL path
          <a
            key={peak.slug}
            href={`/${normalizeState(peak.state_slug)}/hikes/${peak.slug}`}
            className="flex items-center justify-between group p-2 -mx-2 hover:bg-stone-50 rounded-lg transition"
          >
            <div className="flex items-center gap-3">
               <div className="bg-stone-100 h-10 w-10 flex items-center justify-center rounded-full group-hover:bg-emerald-100 group-hover:text-emerald-700 transition">
                 <svg className="w-5 h-5 text-stone-500 group-hover:text-emerald-600" fill="currentColor" viewBox="0 0 24 24">
                   <path d="M14 6l-3.75 5 2.85 3.8-1.6 1.2C9.81 13.75 7 10 7 10l-6 8h22L14 6z"/>
                 </svg>
               </div>
               <div>
                 <div className="text-sm font-bold text-stone-800 group-hover:text-emerald-700 transition">
                    {peak.name}
                 </div>
                 <div className="text-xs text-stone-500">
                    {peak.elevation?.toLocaleString()} ft
                 </div>
               </div>
            </div>
            <div className="text-xs font-mono font-bold text-stone-400 bg-stone-50 px-2 py-1 rounded border border-stone-100">
                {peak.distance_miles}mi
            </div>
          </a>
        ))}
      </div>
    </div>
  );
};

export default NearbyPeaks;