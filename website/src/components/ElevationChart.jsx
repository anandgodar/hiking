import React, { useEffect, useRef, useState } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';

/**
 * Elevation profile — single-series area over distance.
 * Sized to its container (measured, with a resize listener) instead of a
 * fixed 800px, which overflowed every phone. No ResponsiveContainer on
 * purpose: it re-renders unreliably inside Astro islands; a measured width
 * is deterministic.
 */
const ElevationChart = ({ data }) => {
  const wrapRef = useRef(null);
  const [width, setWidth] = useState(0);

  useEffect(() => {
    const measure = () => {
      if (wrapRef.current) setWidth(wrapRef.current.clientWidth);
    };
    measure();
    window.addEventListener('resize', measure);
    return () => window.removeEventListener('resize', measure);
  }, []);

  if (!data || data.length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center text-stone-400 text-sm">
        No Elevation Data
      </div>
    );
  }

  const height = width > 0 && width < 480 ? 200 : 280;

  return (
    <div className="w-full h-full overflow-hidden" ref={wrapRef}>
      <div className="text-xs font-bold uppercase text-stone-400 mb-2 tracking-wider">
        Elevation Profile
      </div>

      {width > 0 && (
        <AreaChart
          width={width}
          height={height}
          data={data}
          margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient id="colorElev" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#059669" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#059669" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
          <XAxis dataKey="mile" type="number" unit="mi" tick={{ fontSize: 12 }} />
          <YAxis
            domain={['auto', 'auto']}
            width={52}
            tick={{ fontSize: 12 }}
            tickFormatter={(v) => `${v.toLocaleString()}ft`}
          />
          <Tooltip
            formatter={(v) => [`${Number(v).toLocaleString()} ft`, 'Elevation']}
            labelFormatter={(l) => `Mile ${l}`}
          />
          <Area type="monotone" dataKey="elev" stroke="#059669" strokeWidth={2} fill="url(#colorElev)" />
        </AreaChart>
      )}
    </div>
  );
};

export default ElevationChart;
