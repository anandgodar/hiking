import { useState } from 'react';

export default function SeasonToggle({ profiles }) {
  const [season, setSeason] = useState('summer');

  const currentData = profiles[season];

  return (
    <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl p-6 shadow-2xl mt-4">
      {/* The Toggle Switch */}
      <div className="flex space-x-2 bg-black/20 p-1 rounded-full w-fit mb-6">
        {['summer', 'shoulder', 'winter'].map((s) => (
          <button
            key={s}
            onClick={() => setSeason(s)}
            className={`px-4 py-1 rounded-full text-sm font-bold uppercase transition-all ${
              season === s ? 'bg-white text-green-900' : 'text-white/60 hover:text-white'
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* The Content */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-white">
        <div>
          <h3 className="text-sm uppercase tracking-wider text-white/50 mb-1">Difficulty</h3>
          <p className="text-2xl font-bold">{currentData.difficulty}</p>
          
          <h3 className="text-sm uppercase tracking-wider text-white/50 mt-4 mb-1">Hazards</h3>
          <ul className="list-disc list-inside text-sm text-white/90">
            {currentData.hazards.map((h, i) => <li key={i}>{h}</li>)}
          </ul>
        </div>
        
        <div className="bg-black/20 rounded-xl p-4">
          <h3 className="text-sm uppercase tracking-wider text-green-400 mb-2">Essential Gear</h3>
          <ul className="space-y-1">
            {currentData.gear.map((g, i) => (
              <li key={i} className="flex items-center text-sm">
                <span className="mr-2">✓</span> {g}
              </li>
            ))}
          </ul>
        </div>
      </div>
      
      <p className="mt-4 text-sm text-white/80 italic border-l-2 border-green-500 pl-3">
        "{currentData.desc}"
      </p>
    </div>
  );
}
