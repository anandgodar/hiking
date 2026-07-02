import React, { useEffect, useState } from 'react';

/**
 * Peak-bagging tracker button (localStorage, no account needed).
 * Two states a hiker cares about: "want to hike it" (saved) and
 * "I climbed it" (completed). Data lives in localStorage under
 * `summitseeker_peaks` and powers the /my-peaks progress page.
 */
const KEY = 'summitseeker_peaks';

const readAll = () => {
  try { return JSON.parse(localStorage.getItem(KEY)) || {}; }
  catch { return {}; }
};

const SavePeakButton = ({ slug, name, stateSlug, stateName, elevation }) => {
  const [status, setStatus] = useState(null); // null | 'saved' | 'completed'

  useEffect(() => {
    setStatus(readAll()[slug]?.status || null);
  }, [slug]);

  const setPeak = (next) => {
    const all = readAll();
    if (next === null) {
      delete all[slug];
    } else {
      all[slug] = {
        name, state_slug: stateSlug, state: stateName, elevation,
        status: next, date: new Date().toISOString().slice(0, 10),
      };
    }
    localStorage.setItem(KEY, JSON.stringify(all));
    setStatus(next);
  };

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={() => setPeak(status === 'completed' ? null : 'completed')}
        className={`px-4 py-2 rounded-lg text-sm font-bold transition-colors ${
          status === 'completed'
            ? 'bg-emerald-600 text-white'
            : 'bg-white border border-stone-300 text-stone-700 hover:border-emerald-600 hover:text-emerald-700'
        }`}
        aria-pressed={status === 'completed'}
      >
        {status === 'completed' ? '✓ Summited' : 'Mark as Summited'}
      </button>
      <button
        onClick={() => setPeak(status === 'saved' ? null : 'saved')}
        className={`px-4 py-2 rounded-lg text-sm font-bold transition-colors ${
          status === 'saved'
            ? 'bg-amber-500 text-white'
            : 'bg-white border border-stone-300 text-stone-700 hover:border-amber-500 hover:text-amber-600'
        }`}
        aria-pressed={status === 'saved'}
      >
        {status === 'saved' ? '★ Saved' : '☆ Save for Later'}
      </button>
      <a href="/my-peaks" className="text-sm text-stone-500 hover:text-emerald-700 underline decoration-dotted">
        My Peaks
      </a>
    </div>
  );
};

export default SavePeakButton;
