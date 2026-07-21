import React from 'react';
import { IconPlane, IconEdit } from './Icons';

export default function Header({ flight_phase, authedSeat, openSeatPicker, isConnected }) {
  const phaseLabel = flight_phase?.replace(/_/g, ' ') || 'Unknown';

  return (
    <header className="app-header">
      <div className="app-header-inner">
        {/* Left: brand */}
        <div className="header-brand">
          <span className="header-brand-icon">
            <IconPlane size={16} />
          </span>
          <span className="header-brand-name">ApexAir</span>
        </div>

        {/* Center: phase pill */}
        <div className="header-center">
          <span className="phase-pill">{phaseLabel}</span>
        </div>

        {/* Right: seat static badge with edit icon + status */}
        <div className="header-right">
          <div className="seat-badge-container">
            <span className="seat-badge">Seat {authedSeat}</span>
            <button className="btn-edit-seat" onClick={openSeatPicker} title="Change Seat" aria-label="Change seat">
              <IconEdit size={12} />
            </button>
          </div>
          
          <div className="status-indicator">
            <span className={`status-dot ${isConnected ? 'status-dot--live' : 'status-dot--offline'}`} />
            <span className="status-label">{isConnected ? 'Active' : 'Offline'}</span>
          </div>
        </div>
      </div>
    </header>
  );
}
