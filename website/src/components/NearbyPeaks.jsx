import React from 'react';

const NearbyPeaks = ({ peaks }) => {
  if (!peaks || peaks.length === 0) return null;

  return (
    <div className="bg-white rounded-2xl p-6 border border-stone-200 shadow-sm mt-6">
      <h3 className="font-serif text-lg font-bold text-stone-900 mb-4 border-b border-stone-100 pb-2">
        Nearby Peaks
      </h3>
      <div className="space-y-3">
        {peaks.map((peak) => (
          <a
            key={peak.slug}
            href={`/${peak.state_slug || 'nh'}/${peak.slug}`}
            className="flex items-center justify-between group p-2 -mx-2 hover:bg-stone-50 rounded-lg transition"
          >
            <div className="flex items-center gap-3">
               <div className="bg-stone-100 text-lg h-10 w-10 flex items-center justify-center rounded-full group-hover:bg-emerald-100 group-hover:text-emerald-700 transition">
                 ⛰️
               </div>
               <div>
                 <div className="text-sm font-bold text-stone-800 group-hover:text-emerald-700 transition">
                    {peak.name}
                 </div>
                 <div className="text-xs text-stone-500">
                    {peak.elevation} ft
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