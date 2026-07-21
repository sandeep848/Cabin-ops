// Crew Command Center: Cabin crew portal for flight context configuration, inventory levels monitoring, and passenger duty queue management. Imported by main.jsx.
import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import './App.css';
import Cabin3DView from './Cabin3DView';

/* ─────────────────────────────────────────
   Constants & Helpers
   ───────────────────────────────────────── */
const API = '';

const INTENT_LABELS = {
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

const getIntentLabel = (intent) => INTENT_LABELS[intent] || 'Crew Call';

const ZONE_LABELS = { fore_cabin: 'Fore', mid_cabin: 'Mid', aft_cabin: 'Aft' };

const PHASES = ['boarding', 'taxi', 'takeoff', 'cruise', 'landing_preparation', 'landing'];
const RESTRICTED_PHASES = new Set(['takeoff', 'landing_preparation', 'landing']);

const SEAT_COLS = ['A', 'B', 'C', 'D', 'E', 'F'];
const TOTAL_ROWS = 30;

const SECTION_LABELS = {
  1:  'First Class',
  11: 'Business',
  21: 'Economy',
};

const formatTime = (isoStr) => {
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

const phaseLabel = (p) =>
  p === 'landing_preparation' ? 'Landing Prep' : (p || '').replace(/_/g, ' ');

const inventoryStockClass = (n) => {
  if (n > 10) return 'good';
  if (n >= 3)  return 'warn';
  return 'low';
};

const capitalize = (str) =>
  (str || '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

/* ─────────────────────────────────────────
   App
   ───────────────────────────────────────── */
export default function App() {
  /* Auth */
  const [token,         setToken]         = useState(sessionStorage.getItem('crew_token') || null);
  const [role,          setRole]           = useState(sessionStorage.getItem('crew_role')  || null);
  const [username,      setUsername]       = useState('');
  const [password,      setPassword]       = useState('');
  const [loginError,    setLoginError]     = useState(null);
  const [loginLoading,  setLoginLoading]   = useState(false);

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
  const [phaseDropdownOpen,  setPhaseDropdownOpen]   = useState(false);
  const [overflowMenuOpen,   setOverflowMenuOpen]    = useState(false);
  const [showOpsGuide,       setShowOpsGuide]        = useState(false);
  const [showClearConfirm,   setShowClearConfirm]    = useState(false);
  const [newAnnouncement,    setNewAnnouncement]      = useState({ speaker: 'Captain', text: '' });
  const [announcementSending,setAnnouncementSending] = useState(false);
  const [inventoryRestocking,setInventoryRestocking] = useState(null);
  const [actionLoading,      setActionLoading]       = useState(null);

  /* Refs for outside-click */
  const phaseRef    = useRef(null);
  const overflowRef = useRef(null);
  const pollingRef  = useRef(null);

  /* ── Outside-click close ─────────────── */
  useEffect(() => {
    const handler = (e) => {
      if (phaseRef.current && !phaseRef.current.contains(e.target)) setPhaseDropdownOpen(false);
      if (overflowRef.current && !overflowRef.current.contains(e.target)) setOverflowMenuOpen(false);
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

  /* ── Auth helpers ────────────────────── */
  const handleLogout = useCallback(() => {
    sessionStorage.removeItem('crew_token');
    sessionStorage.removeItem('crew_role');
    setToken(null);
    setRole(null);
    setTasks([]);
    setAnalytics({ total_tasks: 0, urgent_tasks: 0, by_zone: {} });
    setInventory([]);
    setIsConnected(false);
  }, []);

  const authHeaders = useCallback(() => ({
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  }), [token]);

  /* ── Fetch all data ──────────────────── */
  const fetchData = useCallback(async (tok) => {
    const t = tok || token;
    if (!t) return;
    const hdrs = { 'Content-Type': 'application/json', Authorization: `Bearer ${t}` };
    try {
      const [tasksRes, analyticsRes, contextRes, inventoryRes, announcementsRes] =
        await Promise.all([
          fetch(`${API}/api/crew/tasks`,           { headers: hdrs }),
          fetch(`${API}/api/analytics/summary`,    { headers: hdrs }),
          fetch(`${API}/api/flight-context`),
          fetch(`${API}/api/crew/inventory`,        { headers: hdrs }),
          fetch(`${API}/api/announcements`),
        ]);

      /* Handle 401 on any protected route */
      if (tasksRes.status === 401 || analyticsRes.status === 401 || inventoryRes.status === 401) {
        handleLogout();
        return;
      }

      if (tasksRes.ok)         setTasks(await tasksRes.json());
      if (analyticsRes.ok)     setAnalytics(await analyticsRes.json());
      if (contextRes.ok)       setFlightContext(await contextRes.json());
      if (inventoryRes.ok)     setInventory(await inventoryRes.json());
      if (announcementsRes.ok) setAnnouncements(await announcementsRes.json());

      setIsConnected(true);
    } catch {
      setIsConnected(false);
    }
  }, [token, handleLogout]);

  /* ── Polling ─────────────────────────── */
  useEffect(() => {
    if (!token) return;
    fetchData(token);
    pollingRef.current = setInterval(() => fetchData(token), 2000);
    return () => clearInterval(pollingRef.current);
  }, [token, fetchData]);

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
      setToken(data.token);
      setRole(data.role);
    } catch {
      setLoginError('Connection failed. Check that the server is running.');
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
      /* silent — next poll will correct */
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
      await fetchData();
    } catch { /* ignore */ }
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
      await fetchData();
    } catch { /* ignore */ }
    finally { setActionLoading(null); }
  };

  const clearAllTasks = async () => {
    setShowClearConfirm(false);
    try {
      await fetch(`${API}/api/crew/tasks/clear`, { method: 'POST', headers: authHeaders() });
      await fetchData();
    } catch { /* ignore */ }
  };

  /* ── Inventory restock ───────────────── */
  const restockItem = async (item) => {
    setInventoryRestocking(item);
    try {
      await fetch(`${API}/api/crew/inventory/restock?item=${encodeURIComponent(item)}&quantity=10`, {
        method: 'POST',
        headers: authHeaders(),
      });
      await fetchData();
    } catch { /* ignore */ }
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
      await fetchData();
    } catch { /* ignore */ }
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
  const ACTIVE_STATUSES  = new Set(['pending', 'urgent_pending', 'accepted']);
  const RESOLVED_STATUSES = new Set(['completed', 'rejected', 'delayed', 'answered', 'ignored']);

  const activeTasks   = tasks.filter((t) => ACTIVE_STATUSES.has(t.status));
  const resolvedTasks = tasks.filter((t) => RESOLVED_STATUSES.has(t.status));

  /* Deduplicate: group by seat+intent for pending/urgent_pending */
  const groupedActive = (() => {
    const map = new Map();
    const order = [];
    for (const task of activeTasks) {
      const canGroup = task.status === 'pending' || task.status === 'urgent_pending';
      const key = canGroup ? `${task.seat}||${task.intent}` : `__solo__${task.id}`;
      if (map.has(key)) {
        const item = map.get(key);
        item.count += 1;
        item.ids.push(task.id);
      } else {
        map.set(key, { ...task, count: 1, ids: [task.id] });
        order.push(key);
      }
    }
    return order.map((k) => map.get(k));
  })();

  /* ── Seat → active task map ──────────── */
  const seatTaskMap = (() => {
    const m = new Map();
    for (const t of activeTasks) {
      if (!m.has(t.seat) || t.urgency === 'high') m.set(t.seat, t);
    }
    /* Also track completed for map color */
    for (const t of resolvedTasks) {
      if (!m.has(t.seat) && t.status === 'completed') m.set(t.seat, t);
    }
    return m;
  })();

  /* ── Zone totals ─────────────────────── */
  const zoneCounts = analytics.by_zone || {};
  const totalZone  = Object.values(zoneCounts).reduce((a, b) => a + (b || 0), 0) || 1;

  /* ── Resolved task metrics ───────────── */
  const resolvedCount = resolvedTasks.filter((t) => t.status === 'completed').length;

  /* ── Restricted phase ────────────────── */
  const isRestricted = RESTRICTED_PHASES.has(flightContext.flight_phase);

  /* ── Seat class ──────────────────────── */
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

  /* ── Seat class of cabin ─────────────── */
  const cabinClass = (row) => {
    if (row <= 10) return 'First Class';
    if (row <= 20) return 'Business';
    return 'Economy';
  };

  /* ── Status badge label (resolved) ──── */
  const resolvedLabel = (status) => {
    if (status === 'completed') return 'Fulfilled';
    if (status === 'answered')  return 'Answered';
    if (status === 'rejected' || status === 'delayed' || status === 'ignored') return 'Unavailable';
    return status;
  };

  /* ─── LOGIN PAGE ─────────────────────── */
  if (!token) {
    return (
      <div className="login-page">
        <div className="login-card">
          <div className="login-brand">
            <div className="login-icon">✈</div>
            <div className="login-title">ApexAir Crew</div>
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
      {/* ── HEADER ─────────────────────── */}
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
                  onClick={() => { setShowOpsGuide(true); setOverflowMenuOpen(false); }}
                >
                  Operations Guide
                </button>
                <div className="overflow-divider" />
                <button
                  className="overflow-menu-item danger"
                  onClick={() => { setShowClearConfirm(true); setOverflowMenuOpen(false); }}
                >
                  Clear All Requests
                </button>
                <button
                  className="overflow-menu-item"
                  onClick={() => { handleLogout(); setOverflowMenuOpen(false); }}
                >
                  Sign Out
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* ── MAIN LAYOUT ──────────────────── */}
      <div className="main-layout">
        {/* ── SIDEBAR ────────────────────── */}
        <aside className="sidebar">

          {/* Flight Controls */}
          <div className="sidebar-section">
            <div className="section-label">Flight Controls</div>

            <div className="phase-segmented">
              {PHASES.map((p) => (
                <button
                  key={p}
                  className={`phase-seg-btn${flightContext.flight_phase === p ? ' active' : ''}`}
                  onClick={() => updateFlightContext({ flight_phase: p })}
                >
                  {phaseLabel(p)}
                </button>
              ))}
            </div>

            <div className="toggle-row">
              <span className="toggle-label">Fasten Seatbelt Sign</span>
              <label className="toggle-switch">
                <input
                  type="checkbox"
                  checked={!!flightContext.seatbelt_sign}
                  onChange={(e) => updateFlightContext({ seatbelt_sign: e.target.checked })}
                />
                <span className="toggle-slider" />
              </label>
            </div>

            <div className="toggle-row" style={{ marginTop: 8 }}>
              <span className="toggle-label">Meal Service</span>
              <label className="toggle-switch meal">
                <input
                  type="checkbox"
                  checked={!!flightContext.meal_service_active}
                  onChange={(e) => updateFlightContext({ meal_service_active: e.target.checked })}
                />
                <span className="toggle-slider" />
              </label>
            </div>
          </div>

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
          <div className="sidebar-section">
            <div className="section-label">Galley Inventory</div>
            {inventory.length === 0 ? (
              <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>No inventory data</div>
            ) : (
              <div className="inventory-list">
                {inventory.map((inv) => (
                  <div className="inventory-row" key={inv.item}>
                    <span className="inventory-name" title={inv.alternative ? `Alt: ${inv.alternative}` : ''}>
                      {capitalize(inv.item)}
                    </span>
                    <span className={`inventory-count ${inventoryStockClass(inv.stock)}`}>
                      {inv.stock}
                    </span>
                    <button
                      className="btn-restock"
                      disabled={inventoryRestocking === inv.item}
                      onClick={() => restockItem(inv.item)}
                    >
                      {inventoryRestocking === inv.item ? '…' : '+10'}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Broadcast */}
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

        </aside>

        {/* ── QUEUE (center) ─────────────── */}
        <main className="queue">
          <div className="queue-header">
            <h1 className="queue-title">Passenger Duty Queue</h1>
            <span className="queue-count-badge">{activeTasks.length}</span>
          </div>

          <div className="queue-tabs">
            <button
              className={`queue-tab${activeTab === 'active' ? ' active' : ''}`}
              onClick={() => setActiveTab('active')}
            >
              Active <span className="tab-count">{activeTasks.length}</span>
            </button>
            <button
              className={`queue-tab${activeTab === 'resolved' ? ' active' : ''}`}
              onClick={() => setActiveTab('resolved')}
            >
              Resolved <span className="tab-count">{resolvedTasks.length}</span>
            </button>
          </div>

          {/* Restricted phase banner */}
          {isRestricted && (
            <div className="restricted-banner">
              ⚠ Restricted: Cabin crew must remain seated. Only critical alerts are active.
            </div>
          )}

          {/* Cards */}
          <div className="queue-cards">
            {activeTab === 'active' && (
              groupedActive.length === 0 ? (
                <div className="queue-empty">
                  <div className="queue-empty-icon">🛎</div>
                  <div className="queue-empty-text">No active requests — all clear</div>
                </div>
              ) : (
                groupedActive.map((task) => {
                  const urgencyClass = task.urgency === 'high'
                    ? 'urgency-high'
                    : task.urgency === 'medium'
                    ? 'urgency-medium'
                    : '';

                  const isEmergency = task.intent === 'emergency';
                  const restricted  = isRestricted && !isEmergency;
                  const loading     = actionLoading === task.id;

                  return (
                    <div
                      key={task.id}
                      className={`task-card${urgencyClass ? ` ${urgencyClass}` : ''}`}
                    >
                      {/* Card header */}
                      <div className="task-card-header">
                        <div className="task-seat-row">
                          <span className="task-seat" style={{ fontWeight: '700' }}>
                            {getIntentLabel(task.intent)} — Seat {task.seat}{task.count > 1 ? ` (×${task.count})` : ''}
                          </span>
                        </div>
                        <span className="task-zone">
                          {ZONE_LABELS[task.zone] || task.zone} Zone
                        </span>
                      </div>

                      {/* Card body */}
                      <div className="task-card-body">
                        <div className="task-body-left">
                          <div className={`task-intent${urgencyClass ? ` ${urgencyClass}` : ''}`}>
                            {getIntentLabel(task.intent)}
                          </div>
                          {task.action && (
                            <div className="task-action-text" title={task.action}>
                              {task.action}
                            </div>
                          )}
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4, flexShrink: 0 }}>
                          <span className={`status-badge ${task.status}`}>
                            {task.status === 'pending' || task.status === 'urgent_pending'
                              ? 'Requested'
                              : task.status === 'accepted'
                              ? 'In Progress'
                              : task.status}
                          </span>
                          {(task.urgency === 'high' || task.urgency === 'medium') && (
                            <span className={`task-urgency-badge ${task.urgency}`}>
                              {task.urgency}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Meta */}
                      <div className="task-card-meta">
                        <span>ID: #{task.id}</span>
                        <span>·</span>
                        <span>{getIntentLabel(task.intent)}</span>
                        {task.urgency && task.urgency !== 'none' && (
                          <>
                            <span>·</span>
                            <span>urgency: {task.urgency.toUpperCase()}</span>
                          </>
                        )}
                        {task.created_at && (
                          <>
                            <span>·</span>
                            <span>{formatTime(task.created_at)}</span>
                          </>
                        )}
                      </div>

                      {/* Footer / actions */}
                      <div className="task-card-footer">
                        {restricted ? (
                          <button className="btn-restricted" disabled>
                            Restricted (Phase)
                          </button>
                        ) : (task.status === 'pending' || task.status === 'urgent_pending') ? (
                          <button
                            className={`btn-action ${task.urgency === 'high' ? 'fulfill-high' : 'fulfill-med-low'}`}
                            disabled={loading}
                            onClick={() => acceptTask(task.ids || task.id)}
                          >
                            {loading ? 'Loading…' : 'Fulfill Request'}
                          </button>
                        ) : task.status === 'accepted' ? (
                          <button
                            className="btn-action complete"
                            disabled={loading}
                            onClick={() => completeTask(task.ids || task.id)}
                          >
                            {loading ? 'Loading…' : 'Mark Complete'}
                          </button>
                        ) : null}
                      </div>
                    </div>
                  );
                })
              )
            )}

            {activeTab === 'resolved' && (
              resolvedTasks.length === 0 ? (
                <div className="queue-empty">
                  <div className="queue-empty-icon">✓</div>
                  <div className="queue-empty-text">No resolved requests yet</div>
                </div>
              ) : (
                resolvedTasks.map((task) => (
                  <div key={task.id} className="task-card resolved">
                    <div className="task-card-header">
                      <div className="task-seat-row">
                        <span className="task-seat">Seat {task.seat}</span>
                      </div>
                      <span className="task-zone">
                        {ZONE_LABELS[task.zone] || task.zone} Zone
                      </span>
                    </div>

                    <div className="task-card-body">
                      <div className="task-body-left">
                        <div className="task-intent">{getIntentLabel(task.intent)}</div>
                        {task.action && (
                          <div className="task-action-text" title={task.action}>
                            {task.action}
                          </div>
                        )}
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4, flexShrink: 0 }}>
                        <span className={`status-badge ${task.status}`}>
                          {resolvedLabel(task.status)}
                        </span>
                        <span className="task-checkmark">✓</span>
                      </div>
                    </div>

                    <div className="task-card-meta">
                      <span>ID: #{task.id}</span>
                      <span>·</span>
                      <span>{getIntentLabel(task.intent)}</span>
                      {task.created_at && (
                        <>
                          <span>·</span>
                          <span>{formatTime(task.created_at)}</span>
                        </>
                      )}
                    </div>
                  </div>
                ))
              )
            )}
          </div>
        </main>

        {/* ── MAP PANEL ──────────────────── */}
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
                        <button
                          key={col}
                          className={`${seatClassName(seat)}${selectedSeat === seat ? ' selected' : ''}`}
                          onClick={() => handleSeatClick(seat)}
                          title={seat}
                        >
                          {col}
                        </button>
                      );
                    })}
                    <div /> {/* aisle */}
                    {['D', 'E', 'F'].map((col) => {
                      const seat = `${row}${col}`;
                      return (
                        <button
                          key={col}
                          className={`${seatClassName(seat)}${selectedSeat === seat ? ' selected' : ''}`}
                          onClick={() => handleSeatClick(seat)}
                          title={seat}
                        >
                          {col}
                        </button>
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
                    onClick={() => { setSelectedSeat(null); setSelectedSeatBooking(null); }}
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
              This will delete all passenger requests and reset inventory. Are you sure?
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
