import React, { useState, useEffect } from 'react';
import RouteExplorer from './RouteExplorer';
import WeatherCheck from './WeatherCheck';
import NearbyPeaks from './NearbyPeaks';

const TrailDashboard = ({ mountain }) => {
    const [selectedTrail, setSelectedTrail] = useState(mountain.trails?.[0] || {});

    // Safety: Ensure stats exist
    const stats = selectedTrail.stats || {};

    // Coordinate Logic
    const summitLat = mountain.lat;
    const summitLon = mountain.lon;
    const trailStart = selectedTrail.geo?.markers?.start;
    const baseLat = trailStart ? trailStart[0] : summitLat;
    const baseLon = trailStart ? trailStart[1] : summitLon;

    // Helper: Determine difficulty color
    const getDiffColor = (diff) => {
        if (diff === 'Hard' || diff === 'Strenuous') return 'bg-orange-100 text-orange-700 border-orange-200';
        if (diff === 'Moderate') return 'bg-yellow-100 text-yellow-700 border-yellow-200';
        return 'bg-emerald-100 text-emerald-700 border-emerald-200';
    };

    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">

            {/* --- LEFT COLUMN: Guide & Map --- */}
            <div className="lg:col-span-2 space-y-10">

                {/* 1. GUIDE VERDICT (Refined) */}
                <div className="bg-gradient-to-br from-emerald-50 to-white border border-emerald-100 p-6 rounded-3xl shadow-sm flex gap-5 items-start">
                    <div className="bg-white p-3 rounded-2xl shadow-sm text-2xl border border-emerald-50">💡</div>
                    <div>
                        <h3 className="font-bold text-emerald-950 text-lg">Guide's Verdict</h3>
                        <p className="text-emerald-900/70 leading-relaxed text-sm mt-1.5">
                            Viewing: <strong>{selectedTrail.name}</strong>.
                            {selectedTrail.description
                                ? ` ${selectedTrail.description}`
                                : " This route offers a unique perspective. Always check weather conditions before ascending."}
                        </p>
                    </div>
                </div>

                {/* 2. MAP COMPONENT */}
                <RouteExplorer
                    trails={mountain.trails}
                    lat={mountain.lat}
                    lon={mountain.lon}
                    activeTrail={selectedTrail}
                    onTrailSelect={setSelectedTrail}
                />

                {/* 3. RICH TEXT DESCRIPTION (Now supports Images beautifully) */}
                <div className="prose prose-stone prose-lg max-w-none
                    prose-headings:font-serif prose-headings:font-bold
                    prose-a:text-emerald-600 prose-a:no-underline hover:prose-a:underline
                    prose-img:rounded-3xl prose-img:shadow-xl prose-img:border prose-img:border-stone-100 prose-img:my-8 prose-img:w-full prose-img:object-cover
                    prose-blockquote:border-l-4 prose-blockquote:border-emerald-500 prose-blockquote:bg-stone-50 prose-blockquote:py-2 prose-blockquote:px-4 prose-blockquote:rounded-r-lg">

                    <h2 className="text-3xl font-bold text-stone-900 mb-6 flex items-center gap-3">
                        <span className="w-8 h-1 bg-emerald-500 rounded-full block"></span>
                        The Experience
                    </h2>

                    {mountain.generated_description ? (
                        <div dangerouslySetInnerHTML={{ __html: mountain.generated_description }} />
                    ) : (
                        <p className="text-stone-500 italic">Description updating...</p>
                    )}
                </div>
            </div>

            {/* --- RIGHT COLUMN: Sidebar --- */}
            <div className="space-y-8">

                {/* 4. "HIKER PULSE" (Social Signals & Ratings) */}
                <div className="bg-white border border-stone-100 rounded-3xl p-6 shadow-lg shadow-stone-200/40">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="font-bold text-stone-900 text-sm uppercase tracking-wider">Hiker Pulse</h3>
                        <span className="bg-rose-100 text-rose-600 text-[10px] font-bold px-2 py-1 rounded-full uppercase tracking-wide">🔥 Popular</span>
                    </div>

                    <div className="flex items-end gap-2 mb-4">
                        <div className="text-5xl font-black text-stone-800">4.8</div>
                        <div className="mb-1.5">
                            <div className="text-yellow-400 text-sm">★★★★★</div>
                            <div className="text-xs text-stone-400 font-medium">124 Reviews</div>
                        </div>
                    </div>
                    <div className="text-xs text-stone-500 border-t border-stone-100 pt-3 flex items-center gap-2">
                        <span className="flex -space-x-2">
                            <div className="w-6 h-6 rounded-full bg-stone-200 border-2 border-white"></div>
                            <div className="w-6 h-6 rounded-full bg-stone-300 border-2 border-white"></div>
                            <div className="w-6 h-6 rounded-full bg-stone-400 border-2 border-white"></div>
                        </span>
                        <span><strong>94%</strong> of hikers recommend this route.</span>
                    </div>
                </div>

                {/* 5. REDESIGNED ROUTE STATS (Grid Layout) */}
                <div className="bg-white border border-stone-200 rounded-3xl overflow-hidden shadow-sm">
                    <div className="bg-stone-50 p-4 border-b border-stone-100 flex justify-between items-center">
                        <h3 className="font-bold text-stone-700 text-sm">Route Vitals</h3>
                        <span className={`text-[10px] font-bold px-2 py-1 rounded border ${getDiffColor(stats.difficulty)} uppercase`}>
                            {stats.difficulty || 'Hard'}
                        </span>
                    </div>

                    <div className="p-2">
                        <div className="grid grid-cols-2">
                            {/* Distance */}
                            <div className="p-4 border-r border-b border-stone-100 hover:bg-stone-50 transition-colors">
                                <div className="text-stone-400 text-[10px] uppercase font-bold tracking-wider mb-1">Distance</div>
                                <div className="text-xl font-black text-stone-800 flex items-baseline gap-1">
                                    {stats.distance || 0}<span className="text-xs font-normal text-stone-500">mi</span>
                                </div>
                            </div>
                            {/* Elevation */}
                            <div className="p-4 border-b border-stone-100 hover:bg-stone-50 transition-colors">
                                <div className="text-stone-400 text-[10px] uppercase font-bold tracking-wider mb-1">Gain</div>
                                <div className="text-xl font-black text-stone-800 flex items-baseline gap-1">
                                    {stats.gain || 0}<span className="text-xs font-normal text-stone-500">ft</span>
                                </div>
                            </div>
                            {/* Time */}
                            <div className="p-4 border-r border-stone-100 hover:bg-stone-50 transition-colors">
                                <div className="text-stone-400 text-[10px] uppercase font-bold tracking-wider mb-1">Avg Time</div>
                                <div className="text-xl font-black text-stone-800 flex items-baseline gap-1">
                                    {stats.time || 0}<span className="text-xs font-normal text-stone-500">h</span>
                                </div>
                            </div>
                            {/* Type (Loop/Out) */}
                            <div className="p-4 hover:bg-stone-50 transition-colors">
                                <div className="text-stone-400 text-[10px] uppercase font-bold tracking-wider mb-1">Type</div>
                                <div className="text-lg font-bold text-stone-800">
                                    Out & Back
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="bg-stone-50 px-4 py-2 text-[10px] text-center text-stone-400 border-t border-stone-100">
                        Selected: {selectedTrail.name}
                    </div>
                </div>

                {/* 6. WEATHER WIDGET */}
                <WeatherCheck
                    lat={summitLat}
                    lon={summitLon}
                    baseLat={baseLat}
                    baseLon={baseLon}
                />

                {/* 7. HAZARDS */}
                {mountain.current_conditions?.risk_factors && (
                    <div className="bg-stone-900 text-stone-300 rounded-3xl p-6 relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-24 h-24 bg-orange-500/10 rounded-full blur-2xl -mr-10 -mt-10"></div>
                        <h3 className="font-bold text-white mb-4 flex items-center gap-2 relative z-10">
                            <span className="text-orange-500">⚠️</span> Hazard Watch
                        </h3>
                        <ul className="space-y-3 text-sm relative z-10">
                            {mountain.current_conditions.risk_factors.map((risk, i) => (
                                <li key={i} className="flex items-start gap-3">
                                    <span className="text-orange-500 mt-0.5 text-[10px]">●</span>
                                    {risk}
                                </li>
                            ))}
                        </ul>
                    </div>
                )}

                <NearbyPeaks peaks={mountain.nearby_peaks} />
            </div>
        </div>
    );
};

export default TrailDashboard;