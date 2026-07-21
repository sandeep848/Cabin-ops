import React from 'react';
import { PHASES, phaseLabel } from './Helpers';

export default function FlightStatusControls({ flightContext, updateFlightContext }) {
  return (
    <div className="sidebar-section">
      <div className="section-label">Flight Controls</div>

      <div className="phase-segmented">
        {PHASES.map((p) => (
          <button
            key={p}
            className={`phase-seg-btn${flightContext.flight_phase === p ? ' active' : ''}`}
            onClick={() => updateFlightContext({ flight_phase: p })}
          >
            {phaseLabel(p)}
          </button>
        ))}
      </div>

      <div className="toggle-row">
        <span className="toggle-label">Fasten Seatbelt Sign</span>
        <label className="toggle-switch">
          <input
            type="checkbox"
            checked={!!flightContext.seatbelt_sign}
            onChange={(e) => updateFlightContext({ seatbelt_sign: e.target.checked })}
          />
          <span className="toggle-slider" />
        </label>
      </div>

      <div className="toggle-row" style={{ marginTop: 8 }}>
        <span className="toggle-label">Meal Service</span>
        <label className="toggle-switch meal">
          <input
            type="checkbox"
            checked={!!flightContext.meal_service_active}
            onChange={(e) => updateFlightContext({ meal_service_active: e.target.checked })}
          />
          <span className="toggle-slider" />
        </label>
      </div>
    </div>
  );
}
