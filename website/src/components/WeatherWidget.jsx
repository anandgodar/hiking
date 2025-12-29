import React, { useEffect, useState } from 'react';

export default function WeatherWidget({ lat, lon, elevation }) {
  const [weather, setWeather] = useState(null);
  const [current, setCurrent] = useState(null);
  const [modelElevation, setModelElevation] = useState(0); // What elevation the API thinks it is
  const [loading, setLoading] = useState(true);

  // PHYSICS CONSTANT: 3.5°F drop per 1000ft (Standard Lapse Rate)
  const LAPSE_RATE = 3.5;

  useEffect(() => {
    async function fetchWeather() {
      try {
        // We add '&elevation=nan' which tells Open-Meteo to return the grid-cell elevation
        const res = await fetch(
          `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max&current_weather=true&temperature_unit=fahrenheit&windspeed_unit=mph&timezone=auto`
        );
        const data = await res.json();

        setWeather(data.daily);
        setCurrent(data.current_weather);
        setModelElevation(data.elevation || elevation); // Capture the model's elevation
        setLoading(false);
      } catch (e) {
        console.error("Weather error", e);
        setLoading(false);
      }
    }
    fetchWeather();
  }, [lat, lon, elevation]);

  // SMART ADJUSTMENT FUNCTION
  const getAdjustedTemp = (apiTemp) => {
    if (!elevation || !modelElevation) return Math.round(apiTemp);

    // Calculate difference (e.g., Real: 4000ft, Model: 2000ft -> Diff: 2000ft)
    const elevationDiff = elevation - modelElevation;

    // Calculate temp drop (e.g., 2.0 * 3.5 = 7 degrees cooler)
    const tempCorrection = (elevationDiff / 1000) * LAPSE_RATE;

    // If we are higher than the model, subtract temp. If lower, add temp.
    return Math.round(apiTemp - tempCorrection);
  };

  const getBaseTemp = (summitTemp) => Math.round(summitTemp + (elevation / 1000 * LAPSE_RATE));

  const getWeatherIcon = (code) => {
    if (code <= 1) return "☀️";
    if (code <= 3) return "⛅";
    if (code <= 60) return "☁️";
    if (code <= 80) return "🌧️";
    if (code >= 95) return "⚡";
    return "❄️";
  };

  if (loading) return <div className="animate-pulse h-48 bg-stone-100 rounded-xl"></div>;
  if (!weather || !current) return null;

  // Apply corrections
  const trueSummitTemp = getAdjustedTemp(current.temperature);
  const estimatedBaseTemp = getBaseTemp(trueSummitTemp);

  return (
    <div className="bg-white border border-stone-200 rounded-2xl p-6 shadow-sm">

      <div className="flex flex-col md:flex-row justify-between items-center mb-6 pb-6 border-b border-stone-100">
        <div className="flex items-center gap-4">
             <div className="text-5xl">{getWeatherIcon(current.weathercode)}</div>
             <div>
                <h3 className="text-xs font-bold uppercase text-stone-400 tracking-widest flex items-center gap-1">
                    Summit Conditions
                    {/* Debug Tooltip */}
                    <span className="cursor-help text-[8px] bg-stone-100 px-1 rounded text-stone-300" title={`Model Elev: ${modelElevation}' vs Real: ${elevation}'`}>ℹ</span>
                </h3>
                <div className="flex items-baseline gap-2">
                    {/* DISPLAY CORRECTED TEMP */}
                    <span className="text-4xl font-black text-stone-800">{trueSummitTemp}°F</span>
                    <span className="text-sm font-bold text-stone-500">Wind: {Math.round(current.windspeed)} mph</span>
                </div>
             </div>
        </div>

        <div className="mt-4 md:mt-0 bg-blue-50 px-4 py-2 rounded-lg text-center">
            <h3 className="text-[10px] font-bold uppercase text-blue-400 tracking-widest">Trailhead (Est.)</h3>
            <span className="text-xl font-bold text-blue-900">~{estimatedBaseTemp}°F</span>
        </div>
      </div>

      <h3 className="text-[10px] font-bold uppercase text-stone-400 mb-3 tracking-widest">7-Day Forecast (Summit Adj.)</h3>
      <div className="grid grid-cols-4 md:grid-cols-7 gap-2">
        {weather.time.map((date, i) => (
          <div key={i} className="text-center p-2 rounded-lg hover:bg-stone-50 transition border border-transparent hover:border-stone-100">
            <p className="text-[10px] font-bold text-stone-400 mb-1">
              {new Date(date).toLocaleDateString('en-US', { weekday: 'short' })}
            </p>
            <div className="text-xl mb-1">{getWeatherIcon(weather.weather_code[i])}</div>
            <div className="flex justify-center gap-1 text-xs">
                {/* Apply correction to forecast as well */}
                <span className="font-bold text-stone-800">{getAdjustedTemp(weather.temperature_2m_max[i])}°</span>
                <span className="text-stone-400">{getAdjustedTemp(weather.temperature_2m_min[i])}°</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}