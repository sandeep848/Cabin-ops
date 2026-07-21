import React from 'react';
import Cabin3DView from '../Cabin3DView';
import { TOTAL_ROWS, SECTION_LABELS, getIntentLabel } from './Helpers';

export default function SeatGrid({
  tasks,
  flightContext,
  selectedSeat,
  setSelectedSeat,
  selectedSeatBooking,
  setSelectedSeatBooking,
  selectedSeatLoading,
  seatTaskMap,
  handleSeatClick,
}) {
  const [hoveredSeat, setHoveredSeat] = React.useState(null);

  const getRequestStatus = (seat) => {
    const t = seatTaskMap.get(seat);
    if (!t || t.status === 'completed') return 'No active requests';
    return getIntentLabel(t.intent) || t.intent;
  };

  const getUrgency = (seat) => {
    const t = seatTaskMap.get(seat);
    if (!t || t.status === 'completed') return null;
    return t.urgency || 'low';
  };

  const getStatusColor = (seat) => {
    const t = seatTaskMap.get(seat);
    if (!t || t.status === 'completed') return 'var(--color-text-secondary)';
    if (t.urgency === 'high' || t.intent === 'emergency' || t.intent === 'medical_assistance') {
      return 'var(--color-danger)';
    }
    if (t.intent === 'screen_issue' || t.intent === 'seat_issue') {
      return 'var(--color-accent)';
    }
    return 'var(--color-warning)';
  };

  const getUrgencyColor = (seat) => {
    const t = seatTaskMap.get(seat);
    if (!t) return 'var(--color-text-muted)';
    if (t.urgency === 'high') return 'var(--color-danger)';
    if (t.urgency === 'medium') return 'var(--color-warning)';
    return 'var(--color-success)';
  };

  const seatClassName = (seat) => {
    const t = seatTaskMap.get(seat);
    if (!t) return 'seat-btn';
    if (t.status === 'completed') return 'seat-btn completed-task';
    
    // Highlight active requests semantically
    if (t.urgency === 'high' || t.intent === 'emergency' || t.intent === 'medical_assistance') {
      return 'seat-btn has-task-high'; // Red / emergency
    }
    if (t.intent === 'screen_issue' || t.intent === 'seat_issue') {
      return 'seat-btn has-task-maintenance'; // Blue / maintenance
    }
    return 'seat-btn has-task-service'; // Amber / service call
  };

  const cabinClass = (row) => {
    if (row <= 10) return 'First Class';
    if (row <= 20) return 'Business';
    return 'Economy';
  };

  const closePopover = () => {
    setSelectedSeat(null);
    setSelectedSeatBooking(null);
  };

  return (
    <aside className="map-panel">
      <div className="map-panel-header">
        <div className="map-panel-title">Cabin Map</div>
        <div className="map-legend">
          <div className="legend-item"><span className="legend-dot available" /> Available</div>
          <div className="legend-item"><span className="legend-dot service" /> Service Call</div>
          <div className="legend-item"><span className="legend-dot maintenance" /> Maintenance</div>
          <div className="legend-item"><span className="legend-dot emergency" /> Priority Emergency</div>
        </div>
      </div>

      <div className="map-scroll" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <Cabin3DView tasks={tasks} flightContext={flightContext} onSeatSelect={handleSeatClick} />
        {/* Column labels */}
        <div className="seat-col-labels">
          <div className="seat-col-label" />
          {['A', 'B', 'C'].map((c) => (
            <div className="seat-col-label" key={c}>{c}</div>
          ))}
          <div className="seat-col-label" />
          {['D', 'E', 'F'].map((c) => (
            <div className="seat-col-label" key={c}>{c}</div>
          ))}
        </div>

        {/* Seat rows */}
        {Array.from({ length: TOTAL_ROWS }, (_, i) => i + 1).map((row) => {
          const showSection = SECTION_LABELS[row];
          return (
            <div key={row}>
              {showSection && (
                <div className="seat-section-label">{showSection}</div>
              )}
              <div className="seat-row">
                <div className="seat-row-num">{row}</div>
                {['A', 'B', 'C'].map((col) => {
                  const seat = `${row}${col}`;
                  return (
                    <div
                      key={col}
                      style={{ position: 'relative', display: 'flex', justifyContent: 'center', alignItems: 'center' }}
                      onMouseEnter={() => setHoveredSeat(seat)}
                      onMouseLeave={() => setHoveredSeat(null)}
                    >
                      <button
                        className={`${seatClassName(seat)}${selectedSeat === seat ? ' selected' : ''}`}
                        onClick={() => handleSeatClick(seat)}
                        title={seat}
                      >
                        {col}
                      </button>
                      {hoveredSeat === seat && (
                        <div
                          className="glass-card"
                          style={{
                            position: 'absolute',
                            bottom: '100%',
                            left: '50%',
                            transform: 'translateX(-50%)',
                            marginBottom: '8px',
                            zIndex: 1000,
                            width: '160px',
                            padding: '8px 10px',
                            fontSize: '11px',
                            lineHeight: '1.4',
                            textAlign: 'left',
                            color: 'var(--color-text-primary)',
                            pointerEvents: 'none',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '4px',
                          }}
                        >
                          <div style={{ fontWeight: 'bold', display: 'flex', justifyContent: 'space-between' }}>
                            <span>Seat {seat}</span>
                            <span style={{ color: 'var(--color-text-secondary)', fontSize: '10px' }}>{cabinClass(row)}</span>
                          </div>
                          <div style={{ borderBottom: '1px solid rgba(255,255,255,0.08)', margin: '2px 0' }} />
                          <div>
                            <span style={{ color: 'var(--color-text-secondary)' }}>Status: </span>
                            <span style={{ color: getStatusColor(seat) }}>{getRequestStatus(seat)}</span>
                          </div>
                          {getUrgency(seat) && (
                            <div>
                              <span style={{ color: 'var(--color-text-secondary)' }}>Urgency: </span>
                              <span style={{ 
                                color: getUrgencyColor(seat), 
                                fontWeight: '600',
                                textTransform: 'uppercase',
                                fontSize: '9px'
                              }}>
                                {getUrgency(seat)}
                              </span>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
                <div /> {/* aisle */}
                {['D', 'E', 'F'].map((col) => {
                  const seat = `${row}${col}`;
                  return (
                    <div
                      key={col}
                      style={{ position: 'relative', display: 'flex', justifyContent: 'center', alignItems: 'center' }}
                      onMouseEnter={() => setHoveredSeat(seat)}
                      onMouseLeave={() => setHoveredSeat(null)}
                    >
                      <button
                        className={`${seatClassName(seat)}${selectedSeat === seat ? ' selected' : ''}`}
                        onClick={() => handleSeatClick(seat)}
                        title={seat}
                      >
                        {col}
                      </button>
                      {hoveredSeat === seat && (
                        <div
                          className="glass-card"
                          style={{
                            position: 'absolute',
                            bottom: '100%',
                            left: '50%',
                            transform: 'translateX(-50%)',
                            marginBottom: '8px',
                            zIndex: 1000,
                            width: '160px',
                            padding: '8px 10px',
                            fontSize: '11px',
                            lineHeight: '1.4',
                            textAlign: 'left',
                            color: 'var(--color-text-primary)',
                            pointerEvents: 'none',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '4px',
                          }}
                        >
                          <div style={{ fontWeight: 'bold', display: 'flex', justifyContent: 'space-between' }}>
                            <span>Seat {seat}</span>
                            <span style={{ color: 'var(--color-text-secondary)', fontSize: '10px' }}>{cabinClass(row)}</span>
                          </div>
                          <div style={{ borderBottom: '1px solid rgba(255,255,255,0.08)', margin: '2px 0' }} />
                          <div>
                            <span style={{ color: 'var(--color-text-secondary)' }}>Status: </span>
                            <span style={{ color: getStatusColor(seat) }}>{getRequestStatus(seat)}</span>
                          </div>
                          {getUrgency(seat) && (
                            <div>
                              <span style={{ color: 'var(--color-text-secondary)' }}>Urgency: </span>
                              <span style={{ 
                                color: getUrgencyColor(seat), 
                                fontWeight: '600',
                                textTransform: 'uppercase',
                                fontSize: '9px'
                              }}>
                                {getUrgency(seat)}
                              </span>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}

        {/* Seat popover */}
        {selectedSeat && (
          <div className="seat-popover">
            <div className="seat-popover-header">
              <span className="seat-popover-title">
                Seat {selectedSeat} — {cabinClass(parseInt(selectedSeat, 10))}
              </span>
              <button
                className="seat-popover-close"
                onClick={closePopover}
                aria-label="Close seat details"
              >
                ×
              </button>
            </div>

            {selectedSeatLoading ? (
              <div className="seat-popover-loading">Fetching passenger info…</div>
            ) : selectedSeatBooking ? (
              <>
                <div className="seat-popover-pax">
                  <span>
                    Passenger:{' '}
                    <span className="pax-name">
                      {selectedSeatBooking.passenger_name || '—'}
                    </span>
                  </span>
                  <span className="pax-ref">
                    {selectedSeatBooking.booking_reference || '—'}
                  </span>
                </div>
                {(() => {
                  const t = seatTaskMap.get(selectedSeat);
                  if (t && t.status !== 'completed') {
                    return (
                      <div className="seat-popover-task">
                        <span className="spop-task-name">{getIntentLabel(t.intent)}</span>
                        <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
                          {t.status === 'accepted' ? 'In Progress' : 'Requested'}
                        </span>
                        {t.action && (
                          <span className="spop-task-action">{t.action}</span>
                        )}
                      </div>
                    );
                  }
                  return <div className="seat-popover-none">No active request</div>;
                })()}
              </>
            ) : (
              <div className="seat-popover-none">No booking data available</div>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}
