import React from 'react';

export const INTENT_LABELS = {
  emergency:           'Safety Alert',
  medical_assistance:  'Medical Assistance',
  allergy_question:    'Allergy Inquiry',
  missed_announcement: 'Announcement Query',
  connection_help:     'Connecting Flight',
  lavatory_question:   'Lavatory Info',
  meal_issue:          'Meal Replacement',
  meal_request:        'Meal & Beverage',
  water_request:       'Drinking Water',
  blanket_request:     'Comfort Amenities',
  screen_issue:        'Screen Issue',
  seat_issue:          'Seat Adjustment',
  child_assistance:    'Child Care',
  complaint:           'Service Dispute',
  out_of_scope:        'General Inquiry',
};

export const getIntentLabel = (intent) => INTENT_LABELS[intent] || 'Crew Call';

export const ZONE_LABELS = { fore_cabin: 'Fore', mid_cabin: 'Mid', aft_cabin: 'Aft' };

export const PHASES = ['boarding', 'taxi', 'takeoff', 'cruise', 'landing_preparation', 'landing'];
export const RESTRICTED_PHASES = new Set(['takeoff', 'landing_preparation', 'landing']);

export const SEAT_COLS = ['A', 'B', 'C', 'D', 'E', 'F'];
export const TOTAL_ROWS = 30;

export const SECTION_LABELS = {
  1:  'First Class',
  11: 'Business',
  21: 'Economy',
};

export const formatTime = (isoStr) => {
  if (!isoStr) return '';
  try {
    const d   = new Date(isoStr);
    const now = new Date();
    const isToday = d.toDateString() === now.toDateString();
    const t = d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
    return isToday
      ? `Today ${t}`
      : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ` ${t}`;
  } catch { return isoStr; }
};

export const phaseLabel = (p) =>
  p === 'landing_preparation' ? 'Landing Prep' : (p || '').replace(/_/g, ' ');

export const inventoryStockClass = (n) => {
  if (n > 10) return 'good';
  if (n >= 3)  return 'warn';
  return 'low';
};

export const capitalize = (str) =>
  (str || '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
