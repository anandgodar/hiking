import React, { useEffect, useState } from 'react';

const WeatherCheck = ({ lat, lon, baseLat, baseLon }) => {
  const [mode, setMode] = useState('summit'); // 'summit' or 'base'
  const [weather, setWeather] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  // Fallback safety
  const safeBaseLat = baseLat || lat;
  const safeBaseLon = baseLon || lon;

  const activeLat = mode === 'summit' ? lat : safeBaseLat;
  const activeLon = mode === 'summit' ? lon : safeBaseLon;

  const isIdentical = (Math.abs(lat - safeBaseLat) < 0.001) && (Math.abs(lon - safeBaseLon) < 0.001);

  useEffect(() => {
    setLoading(true);
    setError(false);

    // Small timeout to prevent flickering if user clicks fast
    const timer = setTimeout(() => {
        const fetchWeather = async () => {
          try {
            if (!activeLat || !activeLon) throw new Error("Missing coordinates");

            const url = `https://api.open-meteo.com/v1/forecast?latitude=${activeLat}&longitude=${activeLon}&current=temperature_2m,weather_code,wind_speed_10m&daily=precipitation_probability_max&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto`;

            const res = await fetch(url);
            const data = await res.json();

            if (data.error || !data.current) throw new Error("Weather API Error");
            setWeather(data);
          } catch (e) {
            setError(true);
          } finally {
            setLoading(false);
          }
        };
        fetchWeather();
    }, 150);

    return () => clearTimeout(timer);
  }, [activeLat, activeLon]);

  const getWeatherIcon = (code) => {
    if (code === undefined) return "❓";
    if (code === 0) return "☀️";
    if (code <= 3) return "⛅";
    if (code >= 71) return "❄️";
    if (code >= 51) return "🌧️";
    return "🌫️";
  };

  const showWeather = !loading && !error && weather && weather.current;

  return (
    // FIX 2: Removed 'h-full'. Use 'w-full' to fit container width, but let height be auto.
    <div className="bg-white border border-stone-200 rounded-2xl overflow-hidden shadow-sm transition-all w-full">
      {/* TABS */}
      <div className="flex border-b border-stone-100">
        <button
            onClick={() => setMode('summit')}
            className={`flex-1 py-3 text-xs font-bold uppercase tracking-wider transition-colors ${mode === 'summit' ? 'bg-sky-50 text-sky-700 border-b-2 border-sky-500' : 'text-stone-400 hover:bg-stone-50'}`}
        >
            🏔️ Summit
        </button>
        <button
            onClick={() => setMode('base')}
            className={`flex-1 py-3 text-xs font-bold uppercase tracking-wider transition-colors ${mode === 'base' ? 'bg-emerald-50 text-emerald-700 border-b-2 border-emerald-500' : 'text-stone-400 hover:bg-stone-50'}`}
        >
            🥾 Trailhead
        </button>
      </div>

      <div className="p-6">
        {loading ? (
            <div className="animate-pulse space-y-4 py-2">
                <div className="h-8 bg-stone-100 rounded w-1/2 mx-auto mb-4"></div>
                <div className="flex gap-4">
                    <div className="h-12 bg-stone-100 rounded w-full"></div>
                    <div className="h-12 bg-stone-100 rounded w-full"></div>
                </div>
            </div>
        ) : showWeather ? (
            <div className="animate-fade-in text-center">
                <div className="text-4xl mb-2 filter drop-shadow-sm">{getWeatherIcon(weather?.current?.weather_code)}</div>
                <div className="text-3xl font-black text-stone-800 tracking-tight">
                    {Math.round(weather?.current?.temperature_2m || 0)}°F
                </div>

                {/* Context Label */}
                <div className="text-[10px] font-bold uppercase text-stone-400 tracking-widest mt-1 mb-4">
                    {mode === 'summit' ? "Summit Conditions" : "Base Conditions"}
                    {isIdentical && mode === 'base' && <span className="block text-orange-400 text-[9px] normal-case">(Est. same as summit)</span>}
                </div>

                <div className="grid grid-cols-2 gap-3">
                    <div className="bg-stone-50 rounded-lg p-2 border border-stone-100">
                        <div className="text-[9px] uppercase text-stone-400 font-bold">Wind</div>
                        <div className="font-bold text-stone-700 text-sm">
                            {Math.round(weather?.current?.wind_speed_10m || 0)} mph
                        </div>
                    </div>
                    <div className="bg-stone-50 rounded-lg p-2 border border-stone-100">
                        <div className="text-[9px] uppercase text-stone-400 font-bold">Precip</div>
                        <div className="font-bold text-stone-700 text-sm">
                            {weather?.daily?.precipitation_probability_max?.[0] || 0}%
                        </div>
                    </div>
                </div>
            </div>
        ) : (
            <div className="text-center py-6">
                <div className="text-2xl mb-2">📡</div>
                <div className="text-sm text-stone-500">Unavailable</div>
            </div>
        )}
      </div>
    </div>
  );
};

export default WeatherCheck;