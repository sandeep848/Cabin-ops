import React, { useState, useEffect, useRef } from 'react';
import { PHASES, phaseLabel } from './Helpers';

export default function Header({
  flightContext,
  updateFlightContext,
  isConnected,
  role,
  onOpenOpsGuide,
  onClearAllRequests,
  onSignOut,
}) {
  const [phaseDropdownOpen, setPhaseDropdownOpen] = useState(false);
  const [overflowMenuOpen, setOverflowMenuOpen] = useState(false);

  const phaseRef = useRef(null);
  const overflowRef = useRef(null);

  useEffect(() => {
    const handler = (e) => {
      if (phaseRef.current && !phaseRef.current.contains(e.target)) {
        setPhaseDropdownOpen(false);
      }
      if (overflowRef.current && !overflowRef.current.contains(e.target)) {
        setOverflowMenuOpen(false);
      }
    };
    const keyHandler = (e) => {
      if (e.key === 'Escape') {
        setPhaseDropdownOpen(false);
        setOverflowMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    document.addEventListener('keydown', keyHandler);
    return () => {
      document.removeEventListener('mousedown', handler);
      document.removeEventListener('keydown', keyHandler);
    };
  }, []);

  return (
    <header className="header">
      {/* Left */}
      <div className="header-left">
        <span className="header-logo-icon">✈</span>
        <span className="header-brand-name">ApexAir</span>
        <div className="header-sep" />
        <span className="header-brand-sub">Crew Command</span>
      </div>

      {/* Center */}
      <div className="header-center">
        {/* Phase pill + dropdown */}
        <div className="phase-dropdown-wrap" ref={phaseRef}>
          <button
            className="status-pill pill-phase"
            onClick={() => setPhaseDropdownOpen((o) => !o)}
            title="Change flight phase"
          >
            ◆ {phaseLabel(flightContext.flight_phase)}
          </button>
          {phaseDropdownOpen && (
            <div className="phase-dropdown">
              {PHASES.map((p) => (
                <button
                  key={p}
                  className={`phase-dropdown-item${flightContext.flight_phase === p ? ' active' : ''}`}
                  onClick={() => {
                    updateFlightContext({ flight_phase: p });
                    setPhaseDropdownOpen(false);
                  }}
                >
                  {phaseLabel(p)}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Seatbelt pill */}
        <button
          className={`status-pill ${flightContext.seatbelt_sign ? 'pill-belt-on' : 'pill-belt-off'}`}
          onClick={() => updateFlightContext({ seatbelt_sign: !flightContext.seatbelt_sign })}
          title="Toggle seatbelt sign"
        >
          {flightContext.seatbelt_sign ? '⚠ Belt ON' : '○ Belt OFF'}
        </button>

        {/* Meal pill */}
        <button
          className={`status-pill ${flightContext.meal_service_active ? 'pill-meal-on' : 'pill-meal-off'}`}
          onClick={() => updateFlightContext({ meal_service_active: !flightContext.meal_service_active })}
          title="Toggle meal service"
        >
          {flightContext.meal_service_active ? '✓ Meals ON' : '✗ Meals OFF'}
        </button>

        {/* Sync dot */}
        <span className="status-pill" style={{ cursor: 'default' }}>
          <span className={`sync-dot ${isConnected ? 'online' : 'offline'}`} />
          {isConnected ? 'Synced' : 'Offline'}
        </span>
      </div>

      {/* Right */}
      <div className="header-right">
        <span className="role-badge">{role || 'crew'}</span>

        <div className="overflow-wrap" ref={overflowRef}>
          <button
            className="btn-overflow"
            onClick={() => setOverflowMenuOpen((o) => !o)}
            title="More options"
            aria-label="More options"
          >
            •••
          </button>
          {overflowMenuOpen && (
            <div className="overflow-menu">
              <button
                className="overflow-menu-item"
                onClick={() => { onOpenOpsGuide(); setOverflowMenuOpen(false); }}
              >
                Operations Guide
              </button>
              <div className="overflow-divider" />
              <button
                className="overflow-menu-item danger"
                onClick={() => { onClearAllRequests(); setOverflowMenuOpen(false); }}
              >
                Clear All Requests
              </button>
              <button
                className="overflow-menu-item"
                onClick={() => { onSignOut(); setOverflowMenuOpen(false); }}
              >
                Sign Out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
