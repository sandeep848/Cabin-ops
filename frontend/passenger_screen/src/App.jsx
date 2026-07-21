// Passenger Portal: Seatback interface for passenger request submission and announcements playback. Imported by main.jsx.
import { useState, useEffect, useRef, useCallback } from 'react';
import './App.css';
import Passenger3DView from './Passenger3DView';

// ─────────────────────────────────────────
// HELPERS & CONSTANTS
// ─────────────────────────────────────────
const API_BASE = '';

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

const getSpeakerClass = (speaker = '') => {
  const s = speaker.toLowerCase();
  if (s.includes('captain')) return 'speaker-pill--captain';
  return 'speaker-pill--crew';
};

const VOICE_SAMPLES = [
  'Could I please get some extra napkins with my meal?',
  'Is the lavatory at the rear of the plane currently available?',
  'I think I may have left my jacket in the overhead bin a few rows back.',
  'Can someone help me adjust my seat? The recline button does not seem to work.',
];

// ─────────────────────────────────────────
// SVG ICONS
// ─────────────────────────────────────────
const IconPlane = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17.8 19.2 16 11l3.5-3.5C21 6 21 4 19 2c-2-2-4-2-5.5-.5L10 5 1.8 6.2c-.5.1-.9.6-.8 1.1l.3 1.4c.1.4.4.8.8.9L8 11.5l-1.5 4-1.5.5c-.4.1-.7.5-.7.9v.4c0 .5.5.9 1 .8l4.2-.7 1 3.1c.2.6.9.9 1.4.6l1.4-.7c.4-.2.6-.6.6-1.1z" />
  </svg>
);

const IconDroplet = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z" />
  </svg>
);

const IconLayers = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="12 2 2 7 12 12 22 7 12 2" />
    <polyline points="2 17 12 22 22 17" />
    <polyline points="2 12 12 17 22 12" />
  </svg>
);

const IconDoor = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M13 4H3v16h10" />
    <path d="M13 4l8 2v12l-8 2V4z" />
    <circle cx="16" cy="12" r="1" fill="currentColor" />
  </svg>
);

const IconBroadcast = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M11 5L6 9H2v6h4l5 4V5z" />
    <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
    <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
  </svg>
);

const IconMic = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
    <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
    <line x1="12" y1="19" x2="12" y2="23" />
    <line x1="8" y1="23" x2="16" y2="23" />
  </svg>
);

const IconStop = ({ size = 12 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <rect x="3" y="3" width="18" height="18" rx="2" />
  </svg>
);

const IconInbox = ({ size = 32 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="22 12 16 12 14 15 10 15 8 12 2 12" />
    <path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" />
  </svg>
);

const IconWarning = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
    <line x1="12" y1="9" x2="12" y2="13" />
    <line x1="12" y1="17" x2="12.01" y2="17" />
  </svg>
);

const IconAlert = ({ size = 12 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <line x1="12" y1="8" x2="12" y2="12" />
    <line x1="12" y1="16" x2="12.01" y2="16" />
  </svg>
);

const IconSend = ({ size = 13 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13" />
    <polygon points="22 2 15 22 11 13 2 9 22 2" />
  </svg>
);

const IconEdit = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 20h9" />
    <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
  </svg>
);

const IconX = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18" />
    <line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);

// ─────────────────────────────────────────
// MAIN APP COMPONENT
// ─────────────────────────────────────────
export default function App() {
  // ── Auth state ──
  const [seat, setSeat] = useState('');
  const [bookingRef, setBookingRef] = useState('');
  const [token, setToken] = useState(sessionStorage.getItem('passenger_token') || null);
  const [authedSeat, setAuthedSeat] = useState(sessionStorage.getItem('passenger_seat') || '');
  const [loginError, setLoginError] = useState(null);
  const [loginLoading, setLoginLoading] = useState(false);

  // ── Seat Picker Modal State ──
  const [showSeatPicker, setShowSeatPicker] = useState(false);
  const [newPickerSeat, setNewPickerSeat] = useState('');
  const [newPickerRef, setNewPickerRef] = useState('');
  const [pickerError, setPickerError] = useState(null);
  const [pickerLoading, setPickerLoading] = useState(false);

  // ── Data state ──
  const [myRequests, setMyRequests] = useState([]);
  const [announcements, setAnnouncements] = useState([]);
  const [flightContext, setFlightContext] = useState({
    flight_phase: 'cruise',
    seatbelt_sign: false,
    meal_service_active: true,
    minutes_to_landing: 90,
  });
  const [isConnected, setIsConnected] = useState(false);

  // ── Request input state ──
  const [requestText, setRequestText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [assistantReply, setAssistantReply] = useState(null);
  const [requestsLoading, setRequestsLoading] = useState(true);

  // ── Voice state ──
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [voiceError, setVoiceError] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);

  const pollRef = useRef(null);
  const recordingTimerRef = useRef(null);
  const transcribeRef = useRef(null);
  const textareaRef = useRef(null);

  // ─────────────────────────────────────────
  // DERIVED
  // ─────────────────────────────────────────
  const { flight_phase, seatbelt_sign } = flightContext;
  const restrictedPhases = ['takeoff', 'landing_preparation', 'landing'];
  const isRestricted = seatbelt_sign === true || restrictedPhases.includes(flight_phase);
  const showAlertBar = isRestricted;
  const hasEmergency = myRequests.some((r) => r.intent === 'emergency' && r.status !== 'completed');

  // ─────────────────────────────────────────
  // FETCH HELPERS
  // ─────────────────────────────────────────
  const authHeaders = useCallback(
    () => ({ Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }),
    [token]
  );

  const handleAuthError = useCallback(() => {
    sessionStorage.removeItem('passenger_token');
    sessionStorage.removeItem('passenger_seat');
    setToken(null);
    setAuthedSeat('');
  }, []);

  const fetchData = useCallback(async () => {
    if (!token) return;
    try {
      const [reqRes, annRes, ctxRes] = await Promise.all([
        fetch(`${API_BASE}/api/passenger/requests?seat=${encodeURIComponent(authedSeat)}`, {
          headers: authHeaders(),
        }),
        fetch(`${API_BASE}/api/announcements`),
        fetch(`${API_BASE}/api/flight-context`),
      ]);

      if (reqRes.status === 401) { handleAuthError(); return; }

      setIsConnected(true);

      if (reqRes.ok) {
        const data = await reqRes.json();
        setMyRequests(Array.isArray(data) ? data : []);
      }
      if (annRes.ok) {
        const data = await annRes.json();
        setAnnouncements(Array.isArray(data) ? data : []);
      }
      if (ctxRes.ok) {
        const data = await ctxRes.json();
        setFlightContext((prev) => ({ ...prev, ...data }));
      }
    } catch {
      setIsConnected(false);
    } finally {
      setRequestsLoading(false);
    }
  }, [token, authedSeat, authHeaders, handleAuthError]);

  // ─────────────────────────────────────────
  // POLLING
  // ─────────────────────────────────────────
  useEffect(() => {
    if (!token) return;
    fetchData();
    pollRef.current = setInterval(fetchData, 3000);
    return () => clearInterval(pollRef.current);
  }, [token, fetchData]);

  // ─────────────────────────────────────────
  // LOGIN
  // ─────────────────────────────────────────
  const handleLogin = async (e) => {
    e.preventDefault();
    const trimmedSeat = seat.trim().toUpperCase();
    const trimmedRef = bookingRef.trim().toUpperCase();
    if (!trimmedSeat || !trimmedRef) {
      setLoginError('Please enter your seat number and booking reference.');
      return;
    }
    setLoginError(null);
    setLoginLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/auth/passenger`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ seat: trimmedSeat, booking_reference: trimmedRef }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setLoginError(err.detail || err.message || 'Invalid seat or booking reference.');
        return;
      }
      const data = await res.json();
      sessionStorage.setItem('passenger_token', data.token);
      sessionStorage.setItem('passenger_seat', trimmedSeat);
      setToken(data.token);
      setAuthedSeat(trimmedSeat);
      setBookingRef(trimmedRef);
      setRequestsLoading(true);
    } catch {
      setLoginError('Could not connect to the server. Please try again.');
    } finally {
      setLoginLoading(false);
    }
  };

  // ─────────────────────────────────────────
  // SEAT PICKER SUBMIT
  // ─────────────────────────────────────────
  const handlePickerSubmit = async (e) => {
    e.preventDefault();
    const s = newPickerSeat.trim().toUpperCase();
    const r = newPickerRef.trim().toUpperCase();
    if (!s || !r) {
      setPickerError('Please enter seat and booking reference.');
      return;
    }
    setPickerError(null);
    setPickerLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/auth/passenger`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ seat: s, booking_reference: r }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setPickerError(err.detail || 'Failed to authenticate new seat.');
        return;
      }
      const data = await res.json();
      sessionStorage.setItem('passenger_token', data.token);
      sessionStorage.setItem('passenger_seat', s);
      setToken(data.token);
      setAuthedSeat(s);
      setBookingRef(r);
      setShowSeatPicker(false);
      setMyRequests([]);
      setRequestsLoading(true);
      fetchData();
    } catch {
      setPickerError('Error connecting to authentication server.');
    } finally {
      setPickerLoading(false);
    }
  };

  const openSeatPicker = () => {
    setNewPickerSeat(authedSeat);
    setNewPickerRef(bookingRef || 'DEMO');
    setPickerError(null);
    setShowSeatPicker(true);
  };

  // ─────────────────────────────────────────
  // SWITCH SEAT / LOGOUT
  // ─────────────────────────────────────────
  const handleSwitchSeat = () => {
    clearInterval(pollRef.current);
    sessionStorage.removeItem('passenger_token');
    sessionStorage.removeItem('passenger_seat');
    setToken(null);
    setAuthedSeat('');
    setSeat('');
    setBookingRef('');
    setMyRequests([]);
    setAnnouncements([]);
    setAssistantReply(null);
    setRequestText('');
    setRequestsLoading(true);
    setIsConnected(false);
    stopVoice();
  };

  // ─────────────────────────────────────────
  // SUBMIT REQUEST
  // ─────────────────────────────────────────
  const handleSubmitRequest = async (text) => {
    const payload = text?.trim() || requestText.trim();
    if (!payload || submitting) return;
    setSubmitting(true);
    setSubmitError(null);
    setAssistantReply(null);
    try {
      const res = await fetch(`${API_BASE}/api/request`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ seat: authedSeat, text: payload, input_modality: 'text' }),
      });
      if (res.status === 401) { handleAuthError(); return; }
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setSubmitError(err.detail || err.message || 'Request failed. Please try again.');
        return;
      }
      const data = await res.json();
      setAssistantReply(data);
      setRequestText('');
      fetchData();
    } catch {
      setSubmitError('Connection error. Please check your connection and try again.');
    } finally {
      setSubmitting(false);
    }
  };

  // ─────────────────────────────────────────
  // QUICK TILE CLICK
  // ─────────────────────────────────────────
  const handleQuickTile = (text) => {
    setRequestText(text);
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
    handleSubmitRequest(text);
  };

  // ─────────────────────────────────────────
  // VOICE SIMULATION
  // ─────────────────────────────────────────
  const stopVoice = useCallback(() => {
    setIsRecording(false);
    setIsTranscribing(false);
    setRecordingSeconds(0);
    clearInterval(recordingTimerRef.current);
    clearTimeout(transcribeRef.current);
  }, []);

  const handleMicClick = () => {
    if (voiceError) {
      setVoiceError(false);
      return;
    }
    if (isTranscribing) return;

    if (isRecording) {
      clearInterval(recordingTimerRef.current);
      setIsRecording(false);

      // Short press simulation produces a voice error
      if (recordingSeconds < 1) {
        setVoiceError(true);
        setRecordingSeconds(0);
        return;
      }

      setRecordingSeconds(0);
      setIsTranscribing(true);

      const phrase = VOICE_SAMPLES[Math.floor(Math.random() * VOICE_SAMPLES.length)];
      let idx = 0;
      setRequestText('');

      const typeChar = () => {
        idx++;
        setRequestText(phrase.slice(0, idx));
        if (idx < phrase.length) {
          transcribeRef.current = setTimeout(typeChar, 35);
        } else {
          setIsTranscribing(false);
        }
      };
      transcribeRef.current = setTimeout(typeChar, 35);
    } else {
      setIsRecording(true);
      setRecordingSeconds(0);
      setAssistantReply(null);
      setSubmitError(null);
      setVoiceError(false);
      recordingTimerRef.current = setInterval(() => {
        setRecordingSeconds((s) => s + 1);
      }, 1000);
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearInterval(pollRef.current);
      clearInterval(recordingTimerRef.current);
      clearTimeout(transcribeRef.current);
    };
  }, []);

  // ─────────────────────────────────────────
  // DERIVED PHASE LABEL
  // ─────────────────────────────────────────
  const phaseLabel = flight_phase?.replace(/_/g, ' ') || 'Unknown';

  // ─────────────────────────────────────────
  // SORTED REQUESTS
  // ─────────────────────────────────────────
  const sortedRequests = [...myRequests].sort(
    (a, b) => new Date(b.created_at) - new Date(a.created_at)
  );

  // ─────────────────────────────────────────
  // RECORDING TIMER DISPLAY
  // ─────────────────────────────────────────
  const formatRecordingTime = (secs) => {
    const m = Math.floor(secs / 60).toString().padStart(2, '0');
    const s = (secs % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  // ─────────────────────────────────────────
  // RENDER — LOGIN
  // ─────────────────────────────────────────
  if (!token) {
    return (
      <div className="login-wrapper">
        <div className="login-card">
          <div className="login-brand">
            <div className="login-logo-row">
              <span className="login-logo-icon">
                <IconPlane size={26} />
              </span>
              <span className="login-wordmark">ApexAir</span>
            </div>
            <span className="login-subtitle">Seatback Assistant</span>
          </div>

          <form className="login-form" onSubmit={handleLogin} noValidate>
            <div className="form-field">
              <label className="form-label" htmlFor="seat-input">
                Seat Number
              </label>
              <input
                id="seat-input"
                className="form-input"
                type="text"
                placeholder="e.g. 12D"
                value={seat}
                onChange={(e) => setSeat(e.target.value)}
                autoComplete="off"
                autoCapitalize="characters"
                spellCheck={false}
                disabled={loginLoading}
              />
            </div>

            <div className="form-field">
              <label className="form-label" htmlFor="booking-ref-input">
                Booking Reference
              </label>
              <input
                id="booking-ref-input"
                className="form-input"
                type="text"
                placeholder="e.g. ABCDEF"
                value={bookingRef}
                onChange={(e) => setBookingRef(e.target.value)}
                autoComplete="off"
                autoCapitalize="characters"
                spellCheck={false}
                disabled={loginLoading}
              />
              <p className="form-helper">
                Use <code>DEMO</code> to access without a reservation
              </p>
            </div>

            {loginError && <p className="login-error">{loginError}</p>}

            <button className="btn-primary" type="submit" disabled={loginLoading}>
              {loginLoading ? (
                <>
                  <span className="spinner" />
                  Verifying…
                </>
              ) : (
                'Access Services'
              )}
            </button>
          </form>
        </div>
      </div>
    );
  }

  // ─────────────────────────────────────────
  // RENDER — MAIN APP
  // ─────────────────────────────────────────
  return (
    <div className="app-layout animate-fadein">
      {/* ── HEADER ── */}
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

      {/* ── SEAT PICKER MODAL ── */}
      {showSeatPicker && (
        <div className="modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) setShowSeatPicker(false); }}>
          <div className="modal-card">
            <div className="modal-header">
              <div className="modal-title">Change Seat</div>
              <button className="btn-close-modal" onClick={() => setShowSeatPicker(false)} aria-label="Close modal">×</button>
            </div>
            <form onSubmit={handlePickerSubmit} className="modal-form">
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
                <button type="button" className="btn-ghost" onClick={() => setShowSeatPicker(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={pickerLoading}>
                  {pickerLoading ? 'Verifying…' : 'Change Seat'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── ALERT BAR ── */}
      {showAlertBar && (
        <div className="alert-bar">
          <div className="alert-bar-inner">
            <div className="alert-bar-row">
              <span className="alert-bar-icon">
                <IconWarning size={14} />
              </span>
              <span className="alert-bar-text">
                {seatbelt_sign
                  ? 'Please fasten your seatbelt — cabin services are temporarily suspended.'
                  : `Services are suspended during ${phaseLabel}. Please remain seated.`}
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
      )}

      {/* ── MAIN CONTENT ── */}
      <main className="main-content">
        {/* ── SECTION 1: GREETING + QUICK TILES ── */}
        <section>
          <p className="greeting-text">Hi, Seat {authedSeat}. How can I help?</p>
          <div className="quick-tiles-container">
            <Passenger3DView onServiceSelect={handleQuickTile} isRestricted={isRestricted} />
          </div>
        </section>

        {/* ── SECTION 2: CUSTOM REQUEST ── */}
        <section>
          <p className="section-label">Ask anything or speak</p>
          <div className="request-card">
            <div className="request-input-wrapper">
              <textarea
                ref={textareaRef}
                className="request-textarea"
                rows={3}
                placeholder="Ask anything or speak"
                value={requestText}
                onChange={(e) => setRequestText(e.target.value)}
                disabled={submitting || isRecording || isTranscribing}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault();
                    handleSubmitRequest();
                  }
                }}
              />

              {/* Mic Icon Inside Textarea wrapper on the right */}
              <button
                className={`btn-mic-inside ${
                  voiceError ? 'state-error' : isRecording ? 'state-recording' : isTranscribing ? 'state-transcribing' : 'state-idle'
                }`}
                onClick={handleMicClick}
                disabled={submitting}
                title={voiceError ? 'Clear error' : isRecording ? 'Stop recording' : isTranscribing ? 'Transcribing…' : 'Start voice input'}
                type="button"
              >
                {voiceError ? (
                  <IconX size={14} />
                ) : isRecording ? (
                  <span className="pulsing-red-dot" />
                ) : isTranscribing ? (
                  <span className="spinner-inside" />
                ) : (
                  <IconMic size={14} />
                )}
              </button>
            </div>

            <div className="request-actions-row">
              <div className="request-actions-left">
                {isRecording && (
                  <span className="recording-timer">{formatRecordingTime(recordingSeconds)}</span>
                )}
                {isTranscribing && (
                  <span className="recording-timer" style={{ color: 'var(--color-accent)' }}>
                    Transcribing…
                  </span>
                )}
                {voiceError && (
                  <span className="recording-timer" style={{ color: 'var(--color-danger)' }}>
                    Voice Input Error
                  </span>
                )}
              </div>

              <div className="request-actions-right">
                <span className="char-count">{requestText.length} / 500</span>
                <button
                  className="btn-send"
                  onClick={() => handleSubmitRequest()}
                  disabled={!requestText.trim() || submitting || isRecording || isTranscribing}
                >
                  {submitting ? (
                    <>
                      <span className="spinner" />
                      Sending…
                    </>
                  ) : (
                    <>
                      <IconSend size={13} />
                      Send request
                    </>
                  )}
                </button>
              </div>
            </div>

            {submitError && <p className="submit-error">{submitError}</p>}

            {/* Assistant reply */}
            {assistantReply && (
              <div className="assistant-reply">
                <div className="assistant-reply-header">
                  <span className="assistant-reply-label">ApexAir Assistant</span>
                  <span
                    className={`assistant-reply-badge ${
                      assistantReply.crew_required
                        ? 'assistant-reply-badge--crew'
                        : 'assistant-reply-badge--auto'
                    }`}
                  >
                    {assistantReply.crew_required ? 'Crew Dispatched' : 'Auto-Answered'}
                  </span>
                </div>
                <p className="assistant-reply-text">
                  {assistantReply.response ||
                    assistantReply.message ||
                    assistantReply.action ||
                    'Your request has been received.'}
                </p>
              </div>
            )}
          </div>
        </section>

        {/* ── SECTION 3: ACTIVE REQUESTS ── */}
        <section>
          <p className="section-label">Your requests</p>
          {requestsLoading ? (
            <div className="requests-list">
              <div className="skeleton-card" />
              <div className="skeleton-card" />
            </div>
          ) : sortedRequests.length === 0 ? (
            <div className="empty-state">
              <span className="empty-state-icon">
                <IconInbox size={32} />
              </span>
              <p className="empty-state-text">
                No active requests. Use the buttons above to get started.
              </p>
            </div>
          ) : (
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
          )}
        </section>

        {/* ── SECTION 4: FLIGHT ANNOUNCEMENTS ── */}
        <section>
          <p className="section-label">Flight announcements</p>
          {announcements.length === 0 ? (
            <p className="announcements-empty">No announcements yet.</p>
          ) : (
            <div className="announcements-list">
              {[...announcements]
                .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
                .map((ann) => (
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
          )}
        </section>
      </main>
    </div>
  );
}
