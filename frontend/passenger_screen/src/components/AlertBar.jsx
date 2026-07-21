import React from 'react';
import { IconWarning, IconAlert } from './Icons';

export default function AlertBar({ seatbelt_sign, flight_phase, hasEmergency }) {
  const phaseLabel = flight_phase?.replace(/_/g, ' ') || 'Unknown';
  const restrictedPhases = ['takeoff', 'landing_preparation', 'landing'];
  const isRestricted = seatbelt_sign === true || restrictedPhases.includes(flight_phase);

  if (!isRestricted) return null;

  return (
    <div className="alert-bar">
      <div className="alert-bar-inner">
        <div className="alert-bar-row">
          <span className="alert-bar-icon">
            <IconWarning size={14} />
          </span>
          <span className="alert-bar-text">
            {restrictedPhases.includes(flight_phase)
              ? `Services are suspended during ${phaseLabel}. Please remain seated.`
              : 'Please fasten your seatbelt — cabin services are temporarily suspended.'}
          </span>
        </div>
        {hasEmergency && (
          <div className="alert-bar-emergency">
            <span className="alert-bar-emergency-icon">
              <IconAlert size={12} />
            </span>
            <span className="alert-bar-emergency-text">
              Emergency alerts still active — a crew member has been notified.
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
