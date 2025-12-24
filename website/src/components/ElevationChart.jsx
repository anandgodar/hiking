import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';

// "DUMB" CHART - No ResponsiveContainer, No Crashes.
const ElevationChart = ({ data }) => {
  if (!data || data.length === 0) {
      return (
          <div className="w-full h-full flex items-center justify-center text-stone-400 text-sm">
              No Elevation Data
          </div>
      );
  }

  return (
    <div className="w-full h-full overflow-hidden">
      <div className="text-xs font-bold uppercase text-stone-400 mb-2 tracking-wider">
          Elevation Profile
      </div>

      {/* FIXED SIZE - This forces the chart to render immediately */}
      {/* We use width="100%" via CSS class on parent, but fixed pixels here for safety */}
      <div className="flex justify-center">
        <AreaChart
            width={800}
            height={280}
            data={data}
            margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
        >
            <defs>
                <linearGradient id="colorElev" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#059669" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#059669" stopOpacity={0}/>
                </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
            <XAxis dataKey="mile" type="number" unit="mi" tick={{fontSize: 12}} />
            <YAxis domain={['auto', 'auto']} width={40} tick={{fontSize: 12}} />
            <Tooltip />
            <Area type="monotone" dataKey="elev" stroke="#059669" strokeWidth={2} fill="url(#colorElev)" />
        </AreaChart>
      </div>
    </div>
  );
};

export default ElevationChart;