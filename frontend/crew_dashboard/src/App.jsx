import { apiFetch as fetch } from './api.js';
// Crew Command Center: Cabin crew portal for flight context configuration, inventory levels monitoring, and passenger duty queue management. Imported by main.jsx.
import { useState, useEffect, useCallback, useMemo } from 'react';
import './App.css';

// Extracted Components
import Header from './components/Header';
import FlightStatusControls from './components/FlightStatusControls';
import InventoryWidget from './components/InventoryWidget';
import AnnouncementBoard from './components/AnnouncementBoard';
import TaskQueue from './components/TaskQueue';
import SeatGrid from './components/SeatGrid';

import {
  RESTRICTED_PHASES,
  ZONE_LABELS,
  capitalize,
} from './components/Helpers';

const API = '';

export default function App() {
  /* Auth */
  const [token,         setToken]         = useState(sessionStorage.getItem('crew_token') || null);
  const [role,          setRole]           = useState(sessionStorage.getItem('crew_role')  || null);
  const [flightId,      setFlightId]       = useState(sessionStorage.getItem('crew_flight_id') || '');
  const [username,      setUsername]       = useState('');
  const [password,      setPassword]       = useState('');
  const [loginError,    setLoginError]     = useState(null);
  const [loginLoading,  setLoginLoading]   = useState(false);

  const [operationError, setOperationError] = useState(null);

  /* Data */
  const [tasks,         setTasks]          = useState([]);
  const [analytics,     setAnalytics]      = useState({ total_tasks: 0, urgent_tasks: 0, by_zone: {} });
  const [inventory,     setInventory]      = useState([]);
  const [announcements, setAnnouncements]  = useState([]);
  const [flightContext, setFlightContext]   = useState({
    flight_phase: 'cruise', seatbelt_sign: false, meal_service_active: true, minutes_to_landing: 90,
  });

  /* UI state */
  const [isConnected,        setIsConnected]        = useState(false);
  const [activeTab,          setActiveTab]           = useState('active');
  const [selectedSeat,       setSelectedSeat]        = useState(null);
  const [selectedSeatBooking, setSelectedSeatBooking] = useState(null);
  const [selectedSeatLoading, setSelectedSeatLoading] = useState(false);
  const [showOpsGuide,       setShowOpsGuide]        = useState(false);
  const [showClearConfirm,   setShowClearConfirm]    = useState(false);
  const [newAnnouncement,    setNewAnnouncement]      = useState({ speaker: 'Captain', text: '' });
  const [announcementSending,setAnnouncementSending] = useState(false);
  const [inventoryRestocking,setInventoryRestocking] = useState(null);
  const [actionLoading,      setActionLoading]       = useState(null);

  /* ── Auth helpers ────────────────────── */
  const handleLogout = useCallback(() => {
    sessionStorage.removeItem('crew_token');
    sessionStorage.removeItem('crew_role');
    sessionStorage.removeItem('crew_flight_id');
    setToken(null);
    setRole(null);
    setFlightId('');
    setTasks([]);
    setAnalytics({ total_tasks: 0, urgent_tasks: 0, by_zone: {} });
    setInventory([]);
    setIsConnected(false);
  }, []);

  useEffect(() => {
    window.addEventListener('cabinops-session-expired', handleLogout);
    return () => window.removeEventListener('cabinops-session-expired', handleLogout);
  }, [handleLogout]);

  const authHeaders = useCallback(() => ({
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  }), [token]);

  /* ── Fetch Helper Actions ────────────── */
  const fetchTasks = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API}/api/crew/tasks?flight_id=${encodeURIComponent(flightId)}`, { headers: authHeaders() });
      if (res.status === 401) { handleLogout(); return; }
      if (res.ok) setTasks(await res.json());
    } catch (err) {
      console.error('Failed to fetch attendant tasks:', err);
    }
  }, [token, flightId, authHeaders, handleLogout]);

  const fetchAnalytics = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API}/api/analytics/summary?flight_id=${encodeURIComponent(flightId)}`, { headers: authHeaders() });
      if (res.status === 401) { handleLogout(); return; }
      if (res.ok) setAnalytics(await res.json());
    } catch (err) {
      console.error('Failed to fetch analytics summary:', err);
    }
  }, [token, flightId, authHeaders, handleLogout]);

  const fetchFlightContext = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/flight-context?flight_id=${encodeURIComponent(flightId)}`);
      if (res.ok) setFlightContext(await res.json());
    } catch (err) {
      console.error('Failed to fetch flight context:', err);
    }
  }, [flightId]);

  const fetchInventory = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API}/api/crew/inventory`, { headers: authHeaders() });
      if (res.status === 401) { handleLogout(); return; }
      if (res.ok) setInventory(await res.json());
    } catch (err) {
      console.error('Failed to fetch inventory:', err);
    }
  }, [token, authHeaders, handleLogout]);

  const fetchAnnouncements = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/announcements?flight_id=${encodeURIComponent(flightId)}`);
      if (res.ok) setAnnouncements(await res.json());
    } catch (err) {
      console.error('Failed to fetch announcements:', err);
    }
  }, [flightId]);

  const fetchData = useCallback(async (tok) => {
    const t = tok || token;
    if (!t) return;
    try {
      await Promise.all([
        fetchTasks(),
        fetchAnalytics(),
        fetchFlightContext(),
        fetchInventory(),
        fetchAnnouncements(),
      ]);
    } catch {
      setIsConnected(false);
    }
  }, [token, fetchTasks, fetchAnalytics, fetchFlightContext, fetchInventory, fetchAnnouncements]);

  /* ── EventSource SSE Connection ───────── */
  useEffect(() => {
    if (!token) return;

    fetchData(token);

    let eventSource;
    let fallbackInterval;

    const connectSSE = () => {
      if (eventSource) eventSource.close();
      if (fallbackInterval) clearInterval(fallbackInterval);

      eventSource = new EventSource(`${API}/api/events?token=${encodeURIComponent(token)}`);

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
            fetchTasks();
            fetchAnalytics();
          } else if (data.topic === 'flight_context') {
            fetchFlightContext();
          } else if (data.topic === 'announcements') {
            fetchAnnouncements();
          } else if (data.topic === 'inventory') {
            fetchInventory();
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
        fallbackInterval = setInterval(() => fetchData(token), 5000);
      };
    };

    connectSSE();

    return () => {
      if (eventSource) eventSource.close();
      if (fallbackInterval) clearInterval(fallbackInterval);
    };
  }, [token, fetchData, fetchTasks, fetchAnalytics, fetchFlightContext, fetchInventory, fetchAnnouncements]);

  /* ── Login ───────────────────────────── */
  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginLoading(true);
    setLoginError(null);
    try {
      const res = await fetch(`${API}/api/auth/crew`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setLoginError(err.detail || 'Invalid credentials. Please try again.');
        return;
      }
      const data = await res.json();
      sessionStorage.setItem('crew_token', data.token);
      sessionStorage.setItem('crew_role',  data.role);
      sessionStorage.setItem('crew_flight_id', data.flight_id);
      setToken(data.token);
      setRole(data.role);
      setFlightId(data.flight_id);
    } catch (error) {
      setLoginError(error.message || 'Connection failed. Check that the server is running.');
    } finally {
      setLoginLoading(false);
    }
  };

  /* ── Update flight context ───────────── */
  const updateFlightContext = useCallback(async (patch) => {
    const next = { ...flightContext, ...patch };
    setFlightContext(next);
    try {
      await fetch(`${API}/api/flight-context`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify(next),
      });
    } catch {
      setOperationError("Flight settings could not be saved. Please try again.");
      fetchFlightContext();
    }
  }, [flightContext, authHeaders]);

  /* ── Task actions ────────────────────── */
  const acceptTask = async (idOrIds) => {
    const ids = Array.isArray(idOrIds) ? idOrIds : [idOrIds];
    const firstId = ids[0];
    setActionLoading(firstId);
    try {
      await Promise.all(
        ids.map(id => fetch(`${API}/api/crew/tasks/${id}/accept`, { method: 'POST', headers: authHeaders() }))
      );
      fetchTasks();
      fetchAnalytics();
    } catch (error) { setOperationError(error.message); }
    finally { setActionLoading(null); }
  };

  const completeTask = async (idOrIds) => {
    const ids = Array.isArray(idOrIds) ? idOrIds : [idOrIds];
    const firstId = ids[0];
    setActionLoading(firstId);
    try {
      await Promise.all(
        ids.map(id => fetch(`${API}/api/crew/tasks/${id}/complete`, { method: 'POST', headers: authHeaders() }))
      );
      fetchTasks();
      fetchAnalytics();
    } catch (error) { setOperationError(error.message); }
    finally { setActionLoading(null); }
  };

  const clearAllTasks = async () => {
    setShowClearConfirm(false);
    try {
      await fetch(`${API}/api/crew/tasks/clear`, { method: 'POST', headers: authHeaders() });
      fetchTasks();
      fetchAnalytics();
    } catch (error) { setOperationError(error.message); }
  };

  /* ── Inventory restock ───────────────── */
  const restockItem = async (item) => {
    setInventoryRestocking(item);
    try {
      await fetch(`${API}/api/crew/inventory/restock?item=${encodeURIComponent(item)}&quantity=10`, {
        method: 'POST',
        headers: authHeaders(),
      });
      fetchInventory();
    } catch (error) { setOperationError(error.message); }
    finally { setInventoryRestocking(null); }
  };

  /* ── Broadcast ───────────────────────── */
  const sendAnnouncement = async () => {
    if (!newAnnouncement.text.trim()) return;
    setAnnouncementSending(true);
    try {
      await fetch(`${API}/api/announcements`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          speaker:   newAnnouncement.speaker,
          text:      newAnnouncement.text,
          timestamp: '',
        }),
      });
      setNewAnnouncement((prev) => ({ ...prev, text: '' }));
      fetchAnnouncements();
    } catch (error) { setOperationError(error.message); }
    finally { setAnnouncementSending(false); }
  };

  /* ── Seat click ──────────────────────── */
  const handleSeatClick = async (seat) => {
    if (selectedSeat === seat) {
      setSelectedSeat(null);
      setSelectedSeatBooking(null);
      return;
    }
    setSelectedSeat(seat);
    setSelectedSeatBooking(null);
    setSelectedSeatLoading(true);
    try {
      const res = await fetch(`${API}/api/crew/bookings/${seat}`, { headers: authHeaders() });
      if (res.ok) setSelectedSeatBooking(await res.json());
      else setSelectedSeatBooking(null);
    } catch {
      setSelectedSeatBooking(null);
    } finally {
      setSelectedSeatLoading(false);
    }
  };

  /* ── Task grouping (active) ──────────── */
  const ACTIVE_STATUSES  = useMemo(() => new Set(['pending', 'urgent_pending', 'accepted', 'delayed']), []);
  const RESOLVED_STATUSES = useMemo(() => new Set(['completed', 'rejected', 'answered', 'ignored']), []);

  const activeTasks   = useMemo(() => tasks.filter((t) => ACTIVE_STATUSES.has(t.status)), [tasks, ACTIVE_STATUSES]);
  const resolvedTasks = useMemo(() => tasks.filter((t) => RESOLVED_STATUSES.has(t.status)), [tasks, RESOLVED_STATUSES]);

  const groupedActive = useMemo(() => {
    const priority = { high: 0, medium: 1, low: 2, none: 3 };
    return [...activeTasks].sort((a, b) => (priority[a.urgency] ?? 3) - (priority[b.urgency] ?? 3) || a.id - b.id);
  }, [activeTasks]);

  /* ── Seat → active task map ──────────── */
  const seatTaskMap = useMemo(() => {
    const m = new Map();
    for (const t of activeTasks) {
      if (!m.has(t.seat) || t.urgency === 'high') m.set(t.seat, t);
    }
    /* Also track completed for map color */
    for (const t of resolvedTasks) {
      if (!m.has(t.seat) && t.status === 'completed') m.set(t.seat, t);
    }
    return m;
  }, [activeTasks, resolvedTasks]);

  /* ── Zone totals ─────────────────────── */
  const zoneCounts = analytics.by_zone || {};
  const totalZone  = Object.values(zoneCounts).reduce((a, b) => a + (b || 0), 0) || 1;

  /* ── Resolved task metrics ───────────── */
  const resolvedCount = useMemo(() => resolvedTasks.filter((t) => t.status === 'completed').length, [resolvedTasks]);

  /* ── Restricted phase ────────────────── */
  const isRestricted = flightContext.seatbelt_sign || RESTRICTED_PHASES.has(flightContext.flight_phase);

  /* ─── LOGIN PAGE ─────────────────────── */
  if (!token) {
    return (
      <div className="login-page">
        <div className="login-card">
          <div className="login-brand">
            <div className="login-icon">✈</div>
            <div className="login-title">CabinOps Crew</div>
            <div className="login-subtitle">Authorized Crew Access</div>
          </div>

          <form className="login-form" onSubmit={handleLogin}>
            <div className="login-field">
              <label htmlFor="cc-username">Username</label>
              <input
                id="cc-username"
                type="text"
                placeholder="crew"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
            <div className="login-field">
              <label htmlFor="cc-password">Password</label>
              <input
                id="cc-password"
                type="password"
                placeholder="••••••••"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            {loginError && <div className="login-error">{loginError}</div>}

            <button type="submit" className="btn-signin" disabled={loginLoading}>
              {loginLoading ? 'Signing in…' : 'Sign In'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  /* ─── MAIN APP ───────────────────────── */
  return (
    <div className="app">
      {operationError && <div className="operation-error" role="alert">{operationError}<button onClick={() => setOperationError(null)} aria-label="Dismiss error">×</button></div>}
      <Header
        flightContext={flightContext}
        updateFlightContext={updateFlightContext}
        isConnected={isConnected}
        role={role}
        onOpenOpsGuide={() => setShowOpsGuide(true)}
        onClearAllRequests={() => setShowClearConfirm(true)}
        onSignOut={handleLogout}
      />

      {/* ── MAIN LAYOUT ──────────────────── */}
      <div className="main-layout">
        {/* ── SIDEBAR ────────────────────── */}
        <aside className="sidebar">
          {/* Flight Controls */}
          <FlightStatusControls
            flightContext={flightContext}
            updateFlightContext={updateFlightContext}
          />

          {/* Cabin Summary */}
          <div className="sidebar-section">
            <div className="section-label">Cabin Summary</div>

            <div className="metric-row">
              <div className="metric-card">
                <div className="metric-value">{analytics.total_tasks ?? 0}</div>
                <div className="metric-key">Total</div>
              </div>
              <div className="metric-card">
                <div className={`metric-value urgent${analytics.urgent_tasks === 0 ? ' zero' : ''}`}>
                  {analytics.urgent_tasks ?? 0}
                </div>
                <div className="metric-key">Urgent</div>
              </div>
              <div className="metric-card">
                <div className="metric-value resolved">{resolvedCount}</div>
                <div className="metric-key">Resolved</div>
              </div>
            </div>

            <div className="zone-rows">
              {Object.entries(ZONE_LABELS).map(([key, label]) => {
                const count = zoneCounts[key] ?? 0;
                const pct   = Math.round((count / totalZone) * 100);
                return (
                  <div className="zone-row" key={key}>
                    <div className="zone-row-header">
                      <span className="zone-name">{label} Cabin</span>
                      <span className="zone-count">{count}</span>
                    </div>
                    <div className="progress-bar-track">
                      <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Galley Inventory */}
          <InventoryWidget
            inventory={inventory}
            inventoryRestocking={inventoryRestocking}
            restockItem={restockItem}
          />

          {/* Broadcast */}
          <AnnouncementBoard
            newAnnouncement={newAnnouncement}
            setNewAnnouncement={setNewAnnouncement}
            announcementSending={announcementSending}
            sendAnnouncement={sendAnnouncement}
          />
        </aside>

        {/* ── QUEUE (center) ─────────────── */}
        <TaskQueue
          activeTasks={activeTasks}
          resolvedTasks={resolvedTasks}
          groupedActive={groupedActive}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          isRestricted={isRestricted}
          actionLoading={actionLoading}
          acceptTask={acceptTask}
          completeTask={completeTask}
        />

        {/* ── MAP PANEL ──────────────────── */}
        <SeatGrid
          tasks={tasks}
          flightContext={flightContext}
          selectedSeat={selectedSeat}
          setSelectedSeat={setSelectedSeat}
          selectedSeatBooking={selectedSeatBooking}
          setSelectedSeatBooking={setSelectedSeatBooking}
          selectedSeatLoading={selectedSeatLoading}
          seatTaskMap={seatTaskMap}
          handleSeatClick={handleSeatClick}
        />
      </div>

      {/* ── OPERATIONS GUIDE MODAL ─────── */}
      {showOpsGuide && (
        <div className="modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) setShowOpsGuide(false); }}>
          <div className="modal-card">
            <div className="modal-title">Operations Guide</div>
            <div className="modal-body">
              <h4>Flight Phase Controls</h4>
              <p>Use the phase segmented control or header pill to update the current flight phase. Changing to <strong>Takeoff</strong>, <strong>Landing Prep</strong>, or <strong>Landing</strong> activates restricted mode — service buttons are disabled for non-emergency tasks.</p>

              <h4>Seatbelt & Meal Service</h4>
              <p>Toggle the fasten-seatbelt sign and meal service status from the sidebar or the header pills. These are broadcast instantly to the passenger portal.</p>

              <h4>Passenger Duty Queue</h4>
              <ul>
                <li>Tap <strong>Fulfill Request</strong> to accept a passenger call — this changes status to In Progress.</li>
                <li>Tap <strong>Mark Complete</strong> once the service has been delivered.</li>
                <li>Duplicate calls from the same seat with the same intent are automatically grouped and shown with a ×N badge.</li>
                <li>Red left border = High urgency. Amber = Medium. No border = Low.</li>
              </ul>

              <h4>Galley Inventory</h4>
              <p>Stock counts update in real-time. Green = sufficient (&gt;10). Amber = low (3–10). Red = critical (&lt;3). Tap <strong>+10</strong> to restock.</p>

              <h4>Cabin Map</h4>
              <p>Click any seat to see passenger and booking info. Pulsing red seats indicate high-urgency requests.</p>

              <h4>Broadcast</h4>
              <p>Select a speaker, type an announcement, and tap <strong>Broadcast to Cabin</strong>. The message is visible instantly in the passenger portal.</p>

              <h4>Emergency Credentials</h4>
              <p>Demo login: <strong>crew</strong> / <strong>crew_password</strong></p>
            </div>
            <div className="modal-actions">
              <button className="btn-modal-close" onClick={() => setShowOpsGuide(false)}>
                Got it
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── CLEAR CONFIRM MODAL ─────────── */}
      {showClearConfirm && (
        <div className="modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) setShowClearConfirm(false); }}>
          <div className="modal-card">
            <div className="modal-title">Clear All Requests</div>
            <div className="confirm-body">
              This will clear request history for this flight. Inventory stock is preserved.
            </div>
            <div className="modal-actions">
              <button className="btn-modal-cancel" onClick={() => setShowClearConfirm(false)}>
                Cancel
              </button>
              <button className="btn-modal-danger" onClick={clearAllTasks}>
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
