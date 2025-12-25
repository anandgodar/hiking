import React from 'react';

export const SmartTrailAlert = ({ smartLogic }) => {
  // 1. Safety Check: If data is missing, render nothing
  if (!smartLogic?.ui_alert) return null;

  const { title, message } = smartLogic.ui_alert;
  const type = smartLogic.access_type;

  // 2. Logic: Determine colors/icons based on the alert type
  // 'permit_only' or 'closure' gets RED styling
  // 'ferry_required' or others get AMBER styling
  const isDanger = type === 'permit_only' || type === 'closure';

  const bgColor = isDanger ? 'bg-red-50' : 'bg-amber-50';
  const borderColor = isDanger ? 'border-red-500' : 'border-amber-500';
  const textColor = isDanger ? 'text-red-800' : 'text-amber-900';

  // Choose the icon
  const icon = type === 'ferry_required' ? '⛴️' : '⚠️';

  return (
    <div className={`border-l-4 ${borderColor} ${bgColor} p-4 rounded-r-md mb-6 shadow-sm my-4`}>
      <div className="flex">
        <div className="flex-shrink-0 text-2xl mr-3">
          {icon}
        </div>
        <div>
          <h3 className={`text-sm font-bold ${textColor} uppercase tracking-wide`}>
            {title}
          </h3>
          <div className={`mt-1 text-sm ${textColor} opacity-90`}>
            {message}
          </div>
        </div>
      </div>
    </div>
  );
};