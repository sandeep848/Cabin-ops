import React from 'react';

export default function AnnouncementBoard({
  newAnnouncement,
  setNewAnnouncement,
  announcementSending,
  sendAnnouncement,
}) {
  return (
    <div className="sidebar-section">
      <div className="section-label">Broadcast</div>
      <div className="broadcast-form">
        <select
          className="broadcast-select"
          value={newAnnouncement.speaker}
          onChange={(e) => setNewAnnouncement((p) => ({ ...p, speaker: e.target.value }))}
        >
          <option value="Captain">Captain</option>
          <option value="Cabin Crew">Cabin Crew</option>
          <option value="First Officer">First Officer</option>
        </select>
        <textarea
          className="broadcast-textarea"
          rows={3}
          placeholder="Enter announcement text…"
          value={newAnnouncement.text}
          onChange={(e) => setNewAnnouncement((p) => ({ ...p, text: e.target.value }))}
        />
        <button
          className="btn-broadcast"
          disabled={announcementSending || !newAnnouncement.text.trim()}
          onClick={sendAnnouncement}
        >
          {announcementSending ? 'Sending…' : 'Broadcast to Cabin'}
        </button>
      </div>
    </div>
  );
}
