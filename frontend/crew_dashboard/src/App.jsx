import { useState, useEffect, useMemo, useRef } from "react";
import {
  api,
  useCabinData,
  Login,
  Mark,
  Badge,
  Notice,
  Empty,
  ACTIVE,
  label,
  time,
  age,
  BRAND,
} from "./ui";
import "./App.css";

const VIEWS = [
  "Requests",
  "Cabin",
  "Galley",
  "Broadcasts",
  "Activity",
  "Flight settings",
];
const ZONES = { fore_cabin: "Forward", mid_cabin: "Middle", aft_cabin: "Aft" };
const RESTRICTED = [
  "boarding",
  "taxi",
  "takeoff",
  "landing_preparation",
  "landing",
];
const TARGETS = { high: 1, medium: 5, low: 10, none: 10 };
function Drawer({ children, onClose }) {
  const element = useRef(null);
  useEffect(() => {
    const previous = document.activeElement;
    const initialOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    element.current?.querySelector("button")?.focus();
    const keyboard = (event) => {
      if (event.key === "Escape") onClose();
      if (event.key === "Tab") {
        const controls = element.current.querySelectorAll(
          "button:not(:disabled), a, input, select, textarea",
        );
        const first = controls[0],
          last = controls[controls.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", keyboard);
    return () => {
      document.removeEventListener("keydown", keyboard);
      document.body.style.overflow = initialOverflow;
      previous?.focus();
    };
  }, []);
  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside
        ref={element}
        className="request-drawer"
        role="dialog"
        aria-modal="true"
        aria-label="Request details"
        onClick={(event) => event.stopPropagation()}
      >
        {children}
      </aside>
    </div>
  );
}

function RequestTable({
  tasks,
  busy,
  onAction,
  onSelect,
  restricted,
  username,
}) {
  if (!tasks.length)
    return (
      <Empty
        title="Nothing needs your attention"
        detail="Requests matching this view will appear here."
      />
    );
  return (
    <div className="table-scroll">
      <table className="request-table">
        <thead>
          <tr>
            <th>Seat / request</th>
            <th>Zone</th>
            <th>Priority</th>
            <th>State</th>
            <th>Waiting</th>
            <th>
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {tasks.map((task) => {
            const disabled =
              busy === task.id ||
              (restricted && task.urgency !== "high") ||
              (task.assigned_to &&
                task.assigned_to !== username &&
                task.status === "accepted");
            const minutes = age(task.created_at);
            const overdue =
              ["pending", "urgent_pending"].includes(task.status) &&
              minutes >= TARGETS[task.urgency];
            return (
              <tr
                key={task.id}
                className={
                  task.urgency === "high" && ACTIVE.includes(task.status)
                    ? "urgent-row"
                    : ""
                }
              >
                <td>
                  <button
                    className="request-link"
                    onClick={() => onSelect(task)}
                  >
                    <strong>{task.seat}</strong>
                    <span>{label(task.intent)}</span>
                  </button>
                  <small className="cell-meta">
                    #{task.id}
                    {task.assigned_to ? ` · ${task.assigned_to}` : ""}
                  </small>
                </td>
                <td>{ZONES[task.zone]}</td>
                <td>
                  <span className={`priority priority-${task.urgency}`}>
                    {label(task.urgency)}
                  </span>
                </td>
                <td>
                  <Badge status={task.status} />
                </td>
                <td className={overdue ? "overdue" : ""}>
                  {ACTIVE.includes(task.status)
                    ? `${minutes} min`
                    : time(task.completed_at || task.created_at)}
                  {overdue && <small className="cell-meta">Review now</small>}
                </td>
                <td>
                  {["pending", "urgent_pending", "delayed"].includes(
                    task.status,
                  ) ? (
                    <button
                      className="action-button"
                      disabled={disabled}
                      onClick={() => onAction(task, "accept")}
                    >
                      {busy === task.id ? "Saving…" : "Acknowledge"}
                    </button>
                  ) : task.status === "accepted" ? (
                    <button
                      className="action-button complete"
                      disabled={disabled}
                      onClick={() => onAction(task, "complete")}
                    >
                      {busy === task.id ? "Saving…" : "Complete request"}
                    </button>
                  ) : (
                    <button
                      className="text-button"
                      onClick={() => onSelect(task)}
                    >
                      Details
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function App() {
  const [auth, setAuth] = useState(() =>
    JSON.parse(sessionStorage.getItem("cso-crew") || "null"),
  );
  const [view, setView] = useState("Requests");
  const [filter, setFilter] = useState("open");
  const [zone, setZone] = useState("");
  const [search, setSearch] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(null);
  const [selected, setSelected] = useState(null);
  const [speaker, setSpeaker] = useState("Captain");
  const [draft, setDraft] = useState("");
  const [settings, setSettings] = useState(null);
  const settingsDirty = useRef(false);
  const [stockItem, setStockItem] = useState("");
  const [stockQuantity, setStockQuantity] = useState(10);
  const [clock, setClock] = useState(Date.now());
  const data = useCabinData(auth?.token, auth?.flight_id);
  const logout = () => {
    settingsDirty.current = false;
    sessionStorage.removeItem("cso-crew");
    setAuth(null);
    setSelected(null);
  };
  useEffect(() => {
    window.addEventListener("session-expired", logout);
    const timer = setInterval(() => setClock(Date.now()), 30000);
    return () => {
      window.removeEventListener("session-expired", logout);
      clearInterval(timer);
    };
  }, []);
  useEffect(() => {
    if (!settingsDirty.current) setSettings(data.context);
  }, [data.context]);
  useEffect(() => {
    if (selected)
      setSelected(data.tasks.find((task) => task.id === selected.id) || null);
  }, [data.tasks]);
  async function login(payload) {
    const result = await api("/auth/crew", null, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    const next = { ...result, username: payload.username };
    sessionStorage.setItem("cso-crew", JSON.stringify(next));
    setAuth(next);
  }
  async function action(task, operation) {
    setBusy(task.id);
    setNotice("");
    try {
      await api(`/crew/tasks/${task.id}/${operation}`, auth.token, {
        method: "POST",
      });
      await data.reload();
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(null);
    }
  }
  async function broadcast(event) {
    event.preventDefault();
    setBusy("broadcast");
    setNotice("");
    try {
      await api("/announcements", auth.token, {
        method: "POST",
        body: JSON.stringify({ speaker, text: draft.trim() }),
      });
      setDraft("");
      await data.reload();
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(null);
    }
  }
  async function saveSettings(event) {
    event.preventDefault();
    setBusy("settings");
    setNotice("");
    try {
      await api("/flight-context", auth.token, {
        method: "POST",
        body: JSON.stringify(settings),
      });
      settingsDirty.current = false;
      await data.reload();
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(null);
    }
  }
  async function restock(event) {
    event.preventDefault();
    setBusy("stock");
    setNotice("");
    try {
      await api(
        `/crew/inventory/restock?item=${encodeURIComponent(stockItem)}&quantity=${stockQuantity}`,
        auth.token,
        { method: "POST" },
      );
      setStockItem("");
      await data.reload();
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(null);
    }
  }
  const restricted =
    RESTRICTED.includes(data.context.flight_phase) ||
    data.context.seatbelt_sign;
  const tasks = useMemo(
    () =>
      data.tasks
        .filter(
          (task) =>
            (filter === "all" ||
              (filter === "open"
                ? ACTIVE.includes(task.status)
                : filter === "urgent"
                  ? task.urgency === "high" && ACTIVE.includes(task.status)
                  : task.status === filter)) &&
            (!zone || task.zone === zone) &&
            `${task.seat} ${task.intent} ${task.id}`
              .toLowerCase()
              .includes(search.toLowerCase()),
        )
        .sort(
          (a, b) =>
            (a.urgency === "high" ? 0 : a.urgency === "medium" ? 1 : 2) -
              (b.urgency === "high" ? 0 : b.urgency === "medium" ? 1 : 2) ||
            a.id - b.id,
        ),
    [data.tasks, filter, zone, search, clock],
  );
  if (!auth) return <Login type="crew" onLogin={login} />;
  return (
    <div className="workspace">
      <aside className="navigation">
        <div className="brand">
          <Mark />
          <span>
            Cabin Service
            <br />
            <b>Operations</b>
          </span>
        </div>
        <span className="nav-caption">WORKSPACE</span>
        <nav aria-label="Crew workspaces">
          {VIEWS.map((name) => (
            <button
              key={name}
              className={view === name ? "selected" : ""}
              aria-current={view === name ? "page" : undefined}
              onClick={() => {
                setView(name);
                setNotice("");
              }}
            >
              {name}
              {name === "Requests" && data.summary.open_requests > 0 && (
                <span>{data.summary.open_requests}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="nav-bottom">
          <span className="avatar">
            {auth.username.slice(0, 2).toUpperCase()}
          </span>
          <div>
            <strong>{auth.username}</strong>
            <small>Cabin crew</small>
          </div>
        </div>
      </aside>
      <div className="workspace-body">
        <header className="topbar">
          <span>
            Flight <strong>{auth.flight_id}</strong>
            <span className="topbar-divider" />
            Crew workspace
          </span>
          <span className="connection">
            <i className={data.connected ? "connected" : ""} />
            {data.connected ? "Live updates" : "Reconnecting"}
            <button
              className="text-button"
              onClick={data.reload}
              disabled={data.loading}
            >
              Refresh
            </button>
            <button className="text-button" onClick={logout}>
              Sign out
            </button>
          </span>
        </header>
        <main className="workspace-main">
          <div className="page-heading">
            <div>
              <span className="eyebrow">CABIN SERVICE OPERATIONS</span>
              <h1>{view === "Requests" ? "Service requests" : view}</h1>
              <p>
                {
                  {
                    Requests:
                      "Acknowledge, coordinate, and complete passenger service.",
                    Cabin: "Find a seat and review its active requests.",
                    Galley: "Keep a clear view of available cabin supplies.",
                    Broadcasts: "Send a clear message to everyone on board.",
                    Activity: "A chronological record of service operations.",
                    "Flight settings":
                      "Control the service context for this cabin.",
                  }[view]
                }
              </p>
            </div>
            <span className="flight-phase">
              {label(data.context.flight_phase)}
              <small>
                {data.context.seatbelt_sign
                  ? "Seatbelt sign on"
                  : "Seatbelt sign off"}
              </small>
            </span>
          </div>
          <Notice onDismiss={() => setNotice("")}>
            {notice || data.error}
          </Notice>
          {view === "Requests" && (
            <>
              <div className="metrics">
                <button onClick={() => setFilter("open")}>
                  <span>Open requests</span>
                  <strong>{data.summary.open_requests ?? "—"}</strong>
                  <small>Awaiting or receiving service</small>
                </button>
                <button
                  onClick={() => setFilter("urgent")}
                  className={data.summary.urgent_open ? "attention" : ""}
                >
                  <span>Priority attention</span>
                  <strong>{data.summary.urgent_open ?? "—"}</strong>
                  <small>High-priority open requests</small>
                </button>
                <button onClick={() => setFilter("accepted")}>
                  <span>In progress</span>
                  <strong>{data.summary.in_progress ?? "—"}</strong>
                  <small>Acknowledged by cabin crew</small>
                </button>
                <button onClick={() => setFilter("completed")}>
                  <span>Completed</span>
                  <strong>{data.summary.completed ?? "—"}</strong>
                  <small>Service delivered this flight</small>
                </button>
              </div>
              {restricted && (
                <div className="context-notice">
                  Routine service is paused. High-priority requests remain
                  actionable.
                </div>
              )}
              <section className="panel">
                <div className="panel-toolbar">
                  <div className="tabs">
                    {[
                      ["open", "Open"],
                      ["accepted", "In progress"],
                      ["completed", "Completed"],
                      ["all", "All requests"],
                    ].map(([key, title]) => (
                      <button
                        key={key}
                        className={filter === key ? "active" : ""}
                        onClick={() => setFilter(key)}
                      >
                        {title}
                      </button>
                    ))}
                  </div>
                  <div className="table-filters">
                    <input
                      aria-label="Search requests"
                      placeholder="Find seat or request…"
                      value={search}
                      onChange={(event) => setSearch(event.target.value)}
                    />
                    <select
                      aria-label="Cabin zone"
                      value={zone}
                      onChange={(event) => setZone(event.target.value)}
                    >
                      <option value="">All zones</option>
                      {Object.entries(ZONES).map(([key, name]) => (
                        <option key={key} value={key}>
                          {name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                {data.loading ? (
                  <div className="loading" role="status">
                    Loading service requests…
                  </div>
                ) : (
                  <RequestTable
                    tasks={tasks}
                    busy={busy}
                    onAction={action}
                    onSelect={setSelected}
                    restricted={restricted}
                    username={auth.username}
                  />
                )}
                <footer className="panel-footer">
                  <span>{tasks.length} requests shown · up to 500 records</span>
                  <span>
                    Acknowledgement targets: urgent 1 min · standard 10 min
                  </span>
                </footer>
              </section>
            </>
          )}
          {view === "Cabin" && (
            <section className="panel cabin-panel">
              <div className="section-heading">
                <h2>Seat overview</h2>
                <p>
                  Each row represents six seats. Select a highlighted seat to
                  inspect a request.
                </p>
              </div>
              <div className="seat-map">
                {Array.from({ length: 30 }, (_, index) => (
                  <div className="seat-row" key={index}>
                    <span>{index + 1}</span>
                    {"ABCDEF".split("").map((column, position) => {
                      const seat = `${index + 1}${column}`;
                      const task = data.tasks
                        .filter(
                          (item) =>
                            item.seat === seat && ACTIVE.includes(item.status),
                        )
                        .sort(
                          (a, b) =>
                            (b.urgency === "high") - (a.urgency === "high"),
                        )[0];
                      return (
                        <button
                          key={seat}
                          aria-label={`Seat ${seat}${task ? ": " + label(task.intent) : ": no open requests"}`}
                          className={`${position === 3 ? "aisle" : ""} ${task ? "occupied " + (task.urgency === "high" ? "priority-seat" : "") : ""}`}
                          disabled={!task}
                          onClick={() => setSelected(task)}
                        >
                          {column}
                        </button>
                      );
                    })}
                  </div>
                ))}
              </div>
              <p className="muted">
                Filled seats have open requests. Red marks high-priority
                attention.
              </p>
            </section>
          )}
          {view === "Galley" && (
            <div className="two-column">
              <section className="panel">
                <div className="section-heading">
                  <h2>Stock on hand</h2>
                  <p>Reservations reduce stock when a request is dispatched.</p>
                </div>
                <table className="stock-table">
                  <thead>
                    <tr>
                      <th>Item</th>
                      <th>Available</th>
                      <th>Stock level</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.inventory.map((item) => (
                      <tr key={item.item}>
                        <td>{label(item.item)}</td>
                        <td>
                          <strong>{item.stock}</strong>
                        </td>
                        <td>
                          <span
                            className={`badge ${item.stock < 5 ? "badge-delayed" : "badge-completed"}`}
                          >
                            {item.stock === 0
                              ? "Unavailable"
                              : item.stock < 5
                                ? "Running low"
                                : "Available"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
              <form className="panel form-panel" onSubmit={restock}>
                <h2>Record a restock</h2>
                <p className="muted">
                  Add only supplies physically available in the galley.
                </p>
                <label htmlFor="stock-item">Item</label>
                <select
                  id="stock-item"
                  required
                  value={stockItem}
                  onChange={(event) => setStockItem(event.target.value)}
                >
                  <option value="">Select an item</option>
                  {data.inventory.map((item) => (
                    <option key={item.item} value={item.item}>
                      {label(item.item)}
                    </option>
                  ))}
                </select>
                <label htmlFor="stock-quantity">Quantity received</label>
                <input
                  id="stock-quantity"
                  type="number"
                  min="1"
                  max="100"
                  value={stockQuantity}
                  onChange={(event) =>
                    setStockQuantity(Number(event.target.value))
                  }
                />
                <button className="primary" disabled={busy === "stock"}>
                  {busy === "stock" ? "Recording…" : "Record stock"}
                </button>
              </form>
            </div>
          )}
          {view === "Broadcasts" && (
            <div className="two-column">
              <form className="panel form-panel" onSubmit={broadcast}>
                <h2>New announcement</h2>
                <label htmlFor="speaker">Speaker</label>
                <select
                  id="speaker"
                  value={speaker}
                  onChange={(event) => setSpeaker(event.target.value)}
                >
                  {["Captain", "Cabin Crew", "First Officer"].map((value) => (
                    <option key={value}>{value}</option>
                  ))}
                </select>
                <label htmlFor="broadcast-text">Message</label>
                <textarea
                  id="broadcast-text"
                  className="broadcast-textarea"
                  rows="7"
                  maxLength="2000"
                  required
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  placeholder="Write your announcement…"
                />
                <small className="muted">
                  {draft.length} / 2000 characters
                </small>
                <button
                  className="primary"
                  disabled={busy === "broadcast" || !draft.trim()}
                >
                  {busy === "broadcast" ? "Sending…" : "Broadcast to Cabin"}
                </button>
              </form>
              <section className="panel">
                <div className="section-heading">
                  <h2>Recent announcements</h2>
                </div>
                {data.announcements.length ? (
                  data.announcements.map((item) => (
                    <article className="announcement" key={item.id}>
                      <header>
                        <strong>{item.speaker}</strong>
                        <time>{time(item.timestamp)}</time>
                      </header>
                      <p>{item.text}</p>
                    </article>
                  ))
                ) : (
                  <Empty
                    title="No announcements yet"
                    detail="Sent announcements are stored here."
                  />
                )}
              </section>
            </div>
          )}
          {view === "Activity" && (
            <section className="panel">
              <div className="section-heading">
                <h2>Operational history</h2>
                <p>
                  Latest 200 events. Booking references and passenger messages
                  are excluded.
                </p>
              </div>
              {data.audit.length ? (
                <ol className="audit-list">
                  {data.audit.map((event) => (
                    <li key={event.id}>
                      <time>{time(event.created_at)}</time>
                      <div>
                        <strong>
                          {label(event.event.replaceAll(".", " "))}
                        </strong>
                        <p>{event.detail}</p>
                        <small>
                          {event.actor}
                          {event.task_id ? ` · Request #${event.task_id}` : ""}
                        </small>
                      </div>
                    </li>
                  ))}
                </ol>
              ) : (
                <Empty
                  title="No recorded activity"
                  detail="Request creation and crew actions will appear here."
                />
              )}
            </section>
          )}
          {view === "Flight settings" && settings && (
            <form
              className="panel form-panel settings-panel"
              onChangeCapture={() => {
                settingsDirty.current = true;
              }}
              onSubmit={saveSettings}
            >
              <h2>Service context</h2>
              <p className="muted">
                Changes take effect across the passenger and crew interfaces.
              </p>
              <label htmlFor="flight-phase">Flight phase</label>
              <select
                id="flight-phase"
                value={settings.flight_phase || "cruise"}
                onChange={(event) =>
                  setSettings({ ...settings, flight_phase: event.target.value })
                }
              >
                {[
                  "boarding",
                  "taxi",
                  "takeoff",
                  "cruise",
                  "landing_preparation",
                  "landing",
                ].map((value) => (
                  <option key={value} value={value}>
                    {label(value)}
                  </option>
                ))}
              </select>
              <label className="check-label">
                <input
                  type="checkbox"
                  checked={!!settings.seatbelt_sign}
                  onChange={(event) =>
                    setSettings({
                      ...settings,
                      seatbelt_sign: event.target.checked,
                    })
                  }
                />
                Seatbelt sign on
              </label>
              <label className="check-label">
                <input
                  type="checkbox"
                  checked={!!settings.meal_service_active}
                  onChange={(event) =>
                    setSettings({
                      ...settings,
                      meal_service_active: event.target.checked,
                    })
                  }
                />
                Meal service active
              </label>
              <label htmlFor="landing-minutes">Minutes to landing</label>
              <input
                id="landing-minutes"
                type="number"
                min="0"
                max="1440"
                value={settings.minutes_to_landing ?? 90}
                onChange={(event) =>
                  setSettings({
                    ...settings,
                    minutes_to_landing: Number(event.target.value),
                  })
                }
              />
              <button className="primary" disabled={busy === "settings"}>
                {busy === "settings" ? "Saving…" : "Save flight settings"}
              </button>
            </form>
          )}
          <footer className="workspace-footer">
            <span>{BRAND}</span>
            <span>{auth.flight_id} · Operational service workspace</span>
          </footer>
        </main>
      </div>
      {selected && (
        <Drawer onClose={() => setSelected(null)}>
          <header>
            <span className="eyebrow">REQUEST #{selected.id}</span>
            <button
              className="icon-button"
              aria-label="Close request details"
              onClick={() => setSelected(null)}
            >
              ×
            </button>
          </header>
          <h2>Seat {selected.seat}</h2>
          <p>{label(selected.intent)}</p>
          <Badge status={selected.status} />
          <dl>
            <dt>Cabin zone</dt>
            <dd>{ZONES[selected.zone]}</dd>
            <dt>Priority</dt>
            <dd>{label(selected.urgency)}</dd>
            <dt>Received</dt>
            <dd>{time(selected.created_at)}</dd>
            <dt>Assigned to</dt>
            <dd>{selected.assigned_to || "Unassigned"}</dd>
            <dt>Acknowledged</dt>
            <dd>{time(selected.accepted_at)}</dd>
            <dt>Completed</dt>
            <dd>{time(selected.completed_at)}</dd>
          </dl>
          {selected.request_text && (
            <section className="drawer-note">
              <h3>Passenger message</h3>
              <p>{selected.request_text}</p>
            </section>
          )}
          <section className="drawer-note">
            <h3>Service instruction</h3>
            <p>{selected.action}</p>
          </section>
          <h3>Request history</h3>
          <ol className="audit-list compact">
            {data.audit
              .filter((event) => event.task_id === selected.id)
              .map((event) => (
                <li key={event.id}>
                  <time>{time(event.created_at)}</time>
                  <div>
                    <strong>
                      {label(event.event.replace("request.", ""))}
                    </strong>
                    <small>{event.actor}</small>
                  </div>
                </li>
              ))}
          </ol>
          <button className="secondary" onClick={() => setSelected(null)}>
            Back to workspace
          </button>
        </Drawer>
      )}
    </div>
  );
}
