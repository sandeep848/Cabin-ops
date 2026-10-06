import { useState, useEffect, useCallback } from "react";

export const BRAND = "Cabin Service Operations";
export const ACTIVE = ["pending", "urgent_pending", "accepted", "delayed"];
export const label = (value) =>
  String(value || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
export const time = (value) =>
  value
    ? new Date(value).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      })
    : "—";
export const age = (value) =>
  Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 60000));
export async function api(path, token, options = {}) {
  const response = await fetch(`/api${path}`, {
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && token)
      window.dispatchEvent(new Event("session-expired"));
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : `Unable to complete this operation (${response.status}).`,
    );
  }
  return data;
}
export function useCabinData(token, flight, passengerSeat) {
  const [data, setData] = useState({
    tasks: [],
    announcements: [],
    inventory: [],
    audit: [],
    summary: {},
    context: {},
  });
  const [error, setError] = useState("");
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const load = useCallback(async () => {
    if (!token) return;
    try {
      const paths = passengerSeat
        ? [
            `/passenger/requests?seat=${passengerSeat}`,
            `/announcements?flight_id=${flight}`,
            `/flight-context?flight_id=${flight}`,
          ]
        : [
            "/crew/tasks?limit=500",
            `/announcements?flight_id=${flight}`,
            `/flight-context?flight_id=${flight}`,
            "/crew/inventory",
            "/crew/operations",
            "/crew/audit",
          ];
      const values = await Promise.all(paths.map((path) => api(path, token)));
      setData({
        tasks: values[0],
        announcements: values[1],
        context: values[2],
        inventory: values[3] || [],
        summary: values[4] || {},
        audit: values[5] || [],
      });
      setError("");
      setConnected(true);
    } catch (failure) {
      setError(failure.message);
      setConnected(false);
    } finally {
      setLoading(false);
    }
  }, [token, flight, passengerSeat]);
  useEffect(() => {
    if (!token) return;
    load();
    const stream = new EventSource(
      `/api/events?token=${encodeURIComponent(token)}`,
    );
    stream.onmessage = () => load();
    stream.onerror = () => setConnected(false);
    const interval = setInterval(load, 15000);
    window.addEventListener("online", load);
    return () => {
      stream.close();
      clearInterval(interval);
      window.removeEventListener("online", load);
    };
  }, [token, load]);
  return { ...data, error, connected, loading, reload: load };
}
export function Mark() {
  return (
    <svg viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <path
        d="M7 25V10l9-5 9 5v15M7 16h18M16 5v20"
        stroke="currentColor"
        strokeWidth="2"
      />
      <path d="M11 25h10" stroke="currentColor" strokeWidth="2" />
    </svg>
  );
}
export function Badge({ status }) {
  return (
    <span className={`badge badge-${status}`}>
      {{
        urgent_pending: "Awaiting crew",
        pending: "Awaiting crew",
        accepted: "In progress",
        delayed: "Paused",
        answered: "Answered",
        completed: "Completed",
        rejected: "Unavailable",
      }[status] || label(status)}
    </span>
  );
}
export function Notice({ children, onDismiss }) {
  return (
    children && (
      <div className="notice" role="alert">
        <span>{children}</span>
        {onDismiss && (
          <button
            className="icon-button"
            aria-label="Dismiss error"
            onClick={onDismiss}
          >
            ×
          </button>
        )}
      </div>
    )
  );
}
export function Empty({ title, detail }) {
  return (
    <div className="empty">
      <div className="empty-mark">—</div>
      <h3>{title}</h3>
      <p>{detail}</p>
    </div>
  );
}
export function Login({ type, onLogin }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      await onLogin(
        type === "crew"
          ? { username: form.get("username"), password: form.get("password") }
          : {
              seat: form.get("seat").trim().toUpperCase(),
              booking_reference: form.get("reference").trim().toUpperCase(),
            },
      );
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="login">
      <div className="login-story">
        <div className="brand">
          <Mark />
          <span>{BRAND}</span>
        </div>
        <div>
          <span className="eyebrow">
            {type === "crew" ? "CREW WORKSPACE" : "PASSENGER SERVICES"}
          </span>
          <h1>
            {type === "crew" ? (
              <>
                A quieter workspace.
                <br />A more attentive cabin.
              </>
            ) : (
              <>
                Your seat.
                <br />
                Your service.
              </>
            )}
          </h1>
          <p>
            {type === "crew"
              ? "A clear view of every request, from acknowledgement to completion."
              : "Request what you need and follow its progress without leaving your seat."}
          </p>
        </div>
        <span className="story-footer">
          Purpose-built for cabin service coordination
        </span>
      </div>
      <div className="login-form-wrap">
        <form onSubmit={submit} className="login-form">
          <span className="eyebrow">
            {type === "crew" ? "STAFF ACCESS" : "WELCOME ABOARD"}
          </span>
          <h2>
            {type === "crew"
              ? "Sign in to your workspace"
              : "Connect to your seat"}
          </h2>
          <p className="muted">
            {type === "crew"
              ? "Use the credentials provided by your cabin administrator."
              : "Enter the seat and booking reference provided for this flight."}
          </p>
          {type === "crew" ? (
            <>
              <label htmlFor="cc-username">Username</label>
              <input
                id="cc-username"
                name="username"
                autoComplete="username"
                required
              />
              <label htmlFor="cc-password">Password</label>
              <input
                id="cc-password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
              />
            </>
          ) : (
            <>
              <label htmlFor="seat-input">Seat number</label>
              <input
                id="seat-input"
                name="seat"
                placeholder="22A"
                maxLength={3}
                required
              />
              <label htmlFor="booking-ref-input">Booking reference</label>
              <input
                id="booking-ref-input"
                name="reference"
                placeholder="Your booking reference"
                maxLength={20}
                required
              />
            </>
          )}
          <Notice>{error}</Notice>
          <button className="primary" type="submit" disabled={busy}>
            {busy
              ? "Connecting…"
              : type === "crew"
                ? "Sign In"
                : "Connect to seat"}
          </button>
          <p className="login-help">
            {type === "crew"
              ? "Access is restricted to authorized cabin staff."
              : "Need help connecting? Ask a member of the cabin crew."}
          </p>
        </form>
      </div>
    </main>
  );
}
