import React from 'react';

export default function SeatPickerModal({
  isOpen,
  onClose,
  newPickerSeat,
  setNewPickerSeat,
  newPickerRef,
  setNewPickerRef,
  pickerError,
  pickerLoading,
  onSubmit,
}) {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal-card">
        <div className="modal-header">
          <div className="modal-title">Change Seat</div>
          <button className="btn-close-modal" onClick={onClose} aria-label="Close modal">×</button>
        </div>
        <form onSubmit={onSubmit} className="modal-form">
          <div className="form-field">
            <label className="form-label" htmlFor="picker-seat">New Seat Number</label>
            <input
              id="picker-seat"
              className="form-input"
              type="text"
              placeholder="e.g. 12D"
              value={newPickerSeat}
              onChange={(e) => setNewPickerSeat(e.target.value)}
              autoCapitalize="characters"
              required
            />
          </div>
          <div className="form-field">
            <label className="form-label" htmlFor="picker-ref">Booking Reference</label>
            <input
              id="picker-ref"
              className="form-input"
              type="text"
              placeholder="e.g. ABCDEF"
              value={newPickerRef}
              onChange={(e) => setNewPickerRef(e.target.value)}
              autoCapitalize="characters"
              required
            />
          </div>
          {pickerError && <p className="picker-error">{pickerError}</p>}
          <div className="modal-actions">
            <button type="button" className="btn-ghost" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={pickerLoading}>
              {pickerLoading ? 'Verifying…' : 'Change Seat'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
