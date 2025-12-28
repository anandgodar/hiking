import React, { useState } from 'react';
import RouteExplorer from './RouteExplorer';
import WeatherCheck from './WeatherCheck';
import NearbyPeaks from './NearbyPeaks';

/**
 * Trail Dashboard Component - PRODUCTION VERSION
 *
 * REMOVED: Fake "Hiker Pulse" with hardcoded 4.8 rating and 124 reviews
 * REMOVED: Fake "94% of hikers recommend" stat
 * KEPT: All legitimate trail data display
 */
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
        if (diff === 'Hard' || diff === 'Strenuous' || diff === 'Expert') return 'bg-orange-100 text-orange-700 border-orange-200';
        if (diff === 'Moderate') return 'bg-yellow-100 text-yellow-700 border-yellow-200';
        return 'bg-emerald-100 text-emerald-700 border-emerald-200';
    };

    // Check for real user reviews (from sanitized data)
    const userReviews = mountain.user_reviews || { enabled: false, count: 0 };
    const hasRealReviews = userReviews.enabled && userReviews.count > 0;

    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">

            {/* --- LEFT COLUMN: Guide & Map --- */}
            <div className="lg:col-span-2 space-y-10">

                {/* 1. GUIDE VERDICT */}
                <div className="bg-gradient-to-br from-emerald-50 to-white border border-emerald-100 p-6 rounded-3xl shadow-sm flex gap-5 items-start">
                    <div className="bg-white p-3 rounded-2xl shadow-sm text-2xl border border-emerald-50">
                        <svg className="w-6 h-6 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                        </svg>
                    </div>
                    <div>
                        <h3 className="font-bold text-emerald-950 text-lg">Trail Overview</h3>
                        <p className="text-emerald-900/70 leading-relaxed text-sm mt-1.5">
                            Viewing: <strong>{selectedTrail.name}</strong>.
                            {selectedTrail.description
                                ? ` ${selectedTrail.description}`
                                : " Check weather conditions before ascending."}
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

                {/* 3. RICH TEXT DESCRIPTION */}

            </div>

            {/* --- RIGHT COLUMN: Sidebar --- */}
            <div className="space-y-8">

                {/* ROUTE STATS - No fake ratings */}
                <div className="bg-white border border-stone-200 rounded-3xl overflow-hidden shadow-sm">
                    <div className="bg-stone-50 p-4 border-b border-stone-100 flex justify-between items-center">
                        <h3 className="font-bold text-stone-700 text-sm">Route Details</h3>
                        <span className={`text-[10px] font-bold px-2 py-1 rounded border ${getDiffColor(stats.difficulty)} uppercase`}>
                            {stats.difficulty || 'Moderate'}
                        </span>
                    </div>

                    <div className="p-2">
                        <div className="grid grid-cols-2">
                            {/* Distance */}
                            <div className="p-4 border-r border-b border-stone-100 hover:bg-stone-50 transition-colors">
                                <div className="text-stone-400 text-[10px] uppercase font-bold tracking-wider mb-1">Distance</div>
                                <div className="text-xl font-black text-stone-800 flex items-baseline gap-1">
                                    {stats.distance || selectedTrail.distance_miles || 0}<span className="text-xs font-normal text-stone-500">mi</span>
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
                                <div className="text-stone-400 text-[10px] uppercase font-bold tracking-wider mb-1">Est. Time</div>
                                <div className="text-xl font-black text-stone-800 flex items-baseline gap-1">
                                    {stats.time || '-'}<span className="text-xs font-normal text-stone-500">h</span>
                                </div>
                            </div>
                            {/* Type */}
                            <div className="p-4 hover:bg-stone-50 transition-colors">
                                <div className="text-stone-400 text-[10px] uppercase font-bold tracking-wider mb-1">Type</div>
                                <div className="text-lg font-bold text-stone-800">
                                    {selectedTrail.type || 'Out & Back'}
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="bg-stone-50 px-4 py-2 text-[10px] text-center text-stone-400 border-t border-stone-100">
                        Selected: {selectedTrail.name}
                    </div>
                </div>

                {/* WEATHER WIDGET */}
                <WeatherCheck
                    lat={summitLat}
                    lon={summitLon}
                    baseLat={baseLat}
                    baseLon={baseLon}
                />

                {/* HAZARDS */}
                {mountain.current_conditions?.risk_factors && mountain.current_conditions.risk_factors.length > 0 && (
                    <div className="bg-stone-900 text-stone-300 rounded-3xl p-6 relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-24 h-24 bg-orange-500/10 rounded-full blur-2xl -mr-10 -mt-10"></div>
                        <h3 className="font-bold text-white mb-4 flex items-center gap-2 relative z-10">
                            <svg className="w-5 h-5 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                            Hazard Watch
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

                {/* USER REVIEWS PLACEHOLDER - Only show if real reviews exist */}
                {hasRealReviews ? (
                    <div className="bg-white border border-stone-100 rounded-3xl p-6 shadow-lg shadow-stone-200/40">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="font-bold text-stone-900 text-sm uppercase tracking-wider">Community Reviews</h3>
                        </div>
                        <div className="flex items-end gap-2 mb-4">
                            <div className="text-4xl font-black text-stone-800">
                                {userReviews.average_rating?.toFixed(1) || '-'}
                            </div>
                            <div className="mb-1.5">
                                <div className="text-yellow-400 text-sm flex">
                                    {[1,2,3,4,5].map(i => (
                                        <svg key={i} className={`w-4 h-4 ${i <= Math.round(userReviews.average_rating || 0) ? 'text-yellow-400 fill-current' : 'text-stone-200'}`} viewBox="0 0 24 24">
                                            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                                        </svg>
                                    ))}
                                </div>
                                <div className="text-xs text-stone-400 font-medium">{userReviews.count} Reviews</div>
                            </div>
                        </div>
                    </div>
                ) : (
                    /* Info card instead of fake reviews */
                    <div className="bg-gradient-to-br from-blue-50 to-white border border-blue-100 rounded-3xl p-6">
                        <div className="flex items-start gap-3">
                            <svg className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <div>
                                <h4 className="font-bold text-blue-900 text-sm mb-1">Trail Tip</h4>
                                <p className="text-blue-800/70 text-sm">
                                    Check current conditions on AllTrails or local hiking forums before your trip.
                                </p>
                            </div>
                        </div>
                    </div>
                )}

                <NearbyPeaks peaks={mountain.nearby_peaks} />
            </div>
        </div>
    );
};

export default TrailDashboard;