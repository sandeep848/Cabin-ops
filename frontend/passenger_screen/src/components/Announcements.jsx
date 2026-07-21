import React from 'react';

const formatTime = (isoStr) => {
  if (!isoStr) return '';
  try {
    const d = new Date(isoStr);
    const now = new Date();
    const isToday = d.toDateString() === now.toDateString();
    const timeStr = d.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
    return isToday
      ? `Today at ${timeStr}`
      : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ` at ${timeStr}`;
  } catch {
    return isoStr;
  }
};

const getSpeakerClass = (speaker = '') => {
  const s = speaker.toLowerCase();
  if (s.includes('captain')) return 'speaker-pill--captain';
  return 'speaker-pill--crew';
};

export default function Announcements({ announcements }) {
  if (announcements.length === 0) {
    return <p className="announcements-empty">No announcements yet.</p>;
  }

  const sortedAnnouncements = [...announcements].sort(
    (a, b) => new Date(b.timestamp) - new Date(a.timestamp)
  );

  return (
    <div className="announcements-list">
      {sortedAnnouncements.map((ann) => (
        <div key={ann.id} className="announcement-item">
          <div className="announcement-item-meta">
            <span className={`speaker-pill ${getSpeakerClass(ann.speaker)}`}>
              {ann.speaker || 'Crew'}
            </span>
            <span className="announcement-time">{formatTime(ann.timestamp)}</span>
          </div>
          <p className="announcement-text">{ann.text}</p>
        </div>
      ))}
    </div>
  );
}
