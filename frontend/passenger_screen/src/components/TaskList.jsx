import React from 'react';
import { IconInbox } from './Icons';

const getServiceLabel = (intent, action = '') => {
  const map = {
    emergency: 'Safety Alert',
    medical_assistance: 'Medical Assistance',
    allergy_question: 'Allergy Inquiry',
    missed_announcement: 'Announcement Playback',
    connection_help: 'Connecting Flight Info',
    lavatory_question: 'Lavatory Info',
    meal_issue: 'Meal Replacement',
    meal_request: 'Meal & Beverage',
    water_request: 'Drinking Water',
    blanket_request: 'Comfort Amenities',
    screen_issue: 'Screen Troubleshooting',
    seat_issue: 'Seat Adjustment',
    child_assistance: 'Child Care Support',
    complaint: 'Service Coordinator',
    out_of_scope: 'General Inquiry',
  };
  return map[intent] || 'Cabin Service';
};

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

const getStatusBadge = (status) => {
  switch (status) {
    case 'pending':
    case 'urgent_pending':
      return { cls: 'status-badge--pending', label: 'Requested' };
    case 'accepted':
      return { cls: 'status-badge--accepted', label: 'In Progress' };
    case 'completed':
    case 'answered':
      return { cls: 'status-badge--completed', label: 'Fulfilled' };
    case 'delayed':
      return { cls: 'status-badge--delayed', label: 'Paused' };
    case 'rejected':
      return { cls: 'status-badge--rejected', label: 'Unavailable' };
    default:
      return { cls: 'status-badge--pending', label: status };
  }
};

export default function TaskList({ myRequests, requestsLoading }) {
  const sortedRequests = [...myRequests].sort(
    (a, b) => new Date(b.created_at) - new Date(a.created_at)
  );

  if (requestsLoading) {
    return (
      <div className="requests-list">
        <div className="skeleton-card" />
        <div className="skeleton-card" />
      </div>
    );
  }

  if (sortedRequests.length === 0) {
    return (
      <div className="empty-state">
        <span className="empty-state-icon">
          <IconInbox size={32} />
        </span>
        <p className="empty-state-text">
          No active requests. Use the buttons above to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="requests-list">
      {sortedRequests.map((req) => {
        const badge = getStatusBadge(req.status);
        const isUrgent = req.urgency === 'high' || req.status === 'urgent_pending';
        return (
          <div
            key={req.id}
            className={`request-item${isUrgent ? ' request-item--urgent' : ''}`}
          >
            <div className="request-item-top">
              <span className="request-item-service">
                {getServiceLabel(req.intent, req.action)}
              </span>
              <span className={`status-badge ${badge.cls}`}>{badge.label}</span>
            </div>
            {req.action && (
              <p className="request-item-action">{req.action}</p>
            )}
            <p className="request-item-time">{formatTime(req.created_at)}</p>
          </div>
        );
      })}
    </div>
  );
}
