// Passenger Portal: Seatback interface for passenger request submission and announcements playback. Imported by main.jsx.
import { useState, useEffect, useRef, useCallback } from 'react';
import './App.css';
import Passenger3DView from './Passenger3DView';

// Extracted Components
import Header from './components/Header';
import AlertBar from './components/AlertBar';
import RequestForm from './components/RequestForm';
import TaskList from './components/TaskList';
import Announcements from './components/Announcements';
import SeatPickerModal from './components/SeatPickerModal';
import { IconPlane } from './components/Icons';

const API_BASE = '';

const VOICE_SAMPLES = [
  'Could I please get some extra napkins with my meal?',
  'Is the lavatory at the rear of the plane currently available?',
  'I think I may have left my jacket in the overhead bin a few rows back.',
  'Can someone help me adjust my seat? The recline button does not seem to work.',
];

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

  const fetchPassengerRequests = useCallback(async () => {
    if (!token) return;
    try {
      const reqRes = await fetch(`${API_BASE}/api/passenger/requests?seat=${encodeURIComponent(authedSeat)}`, {
        headers: authHeaders(),
      });
      if (reqRes.status === 401) { handleAuthError(); return; }
      if (reqRes.ok) {
        const data = await reqRes.json();
        setMyRequests(Array.isArray(data) ? data : []);
      }
    } catch (err) {
      console.error('Failed to fetch passenger requests:', err);
    }
  }, [token, authedSeat, authHeaders, handleAuthError]);

  const fetchFlightContext = useCallback(async () => {
    try {
      const ctxRes = await fetch(`${API_BASE}/api/flight-context`);
      if (ctxRes.ok) {
        const data = await ctxRes.json();
        setFlightContext((prev) => ({ ...prev, ...data }));
      }
    } catch (err) {
      console.error('Failed to fetch flight context:', err);
    }
  }, []);

  const fetchAnnouncements = useCallback(async () => {
    try {
      const annRes = await fetch(`${API_BASE}/api/announcements`);
      if (annRes.ok) {
        const data = await annRes.json();
        setAnnouncements(Array.isArray(data) ? data : []);
      }
    } catch (err) {
      console.error('Failed to fetch announcements:', err);
    }
  }, []);

  const fetchData = useCallback(async () => {
    if (!token) return;
    try {
      await Promise.all([
        fetchPassengerRequests(),
        fetchFlightContext(),
        fetchAnnouncements(),
      ]);
      setIsConnected(true);
    } catch {
      setIsConnected(false);
    } finally {
      setRequestsLoading(false);
    }
  }, [token, fetchPassengerRequests, fetchFlightContext, fetchAnnouncements]);

  // ─────────────────────────────────────────
  // EVENTSOURCE (SSE) LISTENING
  // ─────────────────────────────────────────
  useEffect(() => {
    if (!token) return;

    // Fetch initial data
    setRequestsLoading(true);
    fetchData();

    let eventSource;
    let fallbackInterval;

    const connectSSE = () => {
      if (eventSource) eventSource.close();
      if (fallbackInterval) clearInterval(fallbackInterval);

      eventSource = new EventSource(`${API_BASE}/api/events?token=${encodeURIComponent(token)}`);

      eventSource.onopen = () => {
        setIsConnected(true);
      };

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.status === 'connected') {
            setIsConnected(true);
            return;
          }
          if (data.topic === 'tasks') {
            fetchPassengerRequests();
          } else if (data.topic === 'flight_context') {
            fetchFlightContext();
          } else if (data.topic === 'announcements') {
            fetchAnnouncements();
          }
        } catch (err) {
          console.error('Failed to parse SSE event data:', err);
        }
      };

      eventSource.onerror = (err) => {
        console.error('SSE event source connection error, falling back to polling:', err);
        setIsConnected(false);
        if (eventSource) {
          eventSource.close();
        }
        // Fallback polling loop if EventSource stream fails
        fallbackInterval = setInterval(fetchData, 5000);
      };
    };

    connectSSE();

    return () => {
      if (eventSource) eventSource.close();
      if (fallbackInterval) clearInterval(fallbackInterval);
    };
  }, [token, fetchData, fetchPassengerRequests, fetchFlightContext, fetchAnnouncements]);

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
      fetchPassengerRequests();
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
      clearInterval(recordingTimerRef.current);
      clearTimeout(transcribeRef.current);
    };
  }, []);

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
      <Header
        flight_phase={flight_phase}
        authedSeat={authedSeat}
        openSeatPicker={openSeatPicker}
        isConnected={isConnected}
      />

      <SeatPickerModal
        isOpen={showSeatPicker}
        onClose={() => setShowSeatPicker(false)}
        newPickerSeat={newPickerSeat}
        setNewPickerSeat={setNewPickerSeat}
        newPickerRef={newPickerRef}
        setNewPickerRef={setNewPickerRef}
        pickerError={pickerError}
        pickerLoading={pickerLoading}
        onSubmit={handlePickerSubmit}
      />

      <AlertBar
        seatbelt_sign={seatbelt_sign}
        flight_phase={flight_phase}
        hasEmergency={hasEmergency}
      />

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
          <RequestForm
            requestText={requestText}
            setRequestText={setRequestText}
            submitting={submitting}
            onSubmit={handleSubmitRequest}
            assistantReply={assistantReply}
            submitError={submitError}
            textareaRef={textareaRef}
            isRecording={isRecording}
            isTranscribing={isTranscribing}
            voiceError={voiceError}
            recordingSeconds={recordingSeconds}
            handleMicClick={handleMicClick}
          />
        </section>

        {/* ── SECTION 3: ACTIVE REQUESTS ── */}
        <section>
          <p className="section-label">Your requests</p>
          <TaskList myRequests={myRequests} requestsLoading={requestsLoading} />
        </section>

        {/* ── SECTION 4: FLIGHT ANNOUNCEMENTS ── */}
        <section>
          <p className="section-label">Flight announcements</p>
          <Announcements announcements={announcements} />
        </section>
      </main>
    </div>
  );
}
