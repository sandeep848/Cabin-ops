import { useState, useEffect, useCallback, useRef } from "react";

export const BRAND = "Cabin Atlas";
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
  const generation = useRef(0);
  const [data, setData] = useState({
    tasks: [],
    announcements: [],
    inventory: [],
    audit: [],
    summary: {},
    context: {},
    profile: {},
    menu: [],
  });
  const [error, setError] = useState("");
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const load = useCallback(async () => {
    if (!token) return;
    const current = generation.current;
    try {
      const paths = passengerSeat
        ? [
            `/passenger/requests?seat=${passengerSeat}`,
            `/announcements?flight_id=${flight}`,
            `/flight-context?flight_id=${flight}`,
            "/flight-profile",
            "/experience/menu",
          ]
        : [
            "/crew/tasks?limit=500",
            `/announcements?flight_id=${flight}`,
            `/flight-context?flight_id=${flight}`,
            "/crew/inventory",
            "/crew/operations",
            "/crew/audit",
            "/flight-profile",
          ];
      const values = await Promise.all(paths.map((path) => api(path, token)));
      if (current !== generation.current) return;
      setData({
        tasks: values[0],
        announcements: values[1],
        context: values[2],
        profile: passengerSeat ? values[3] : values[6],
        menu: passengerSeat ? values[4] : [],
        inventory: passengerSeat ? [] : values[3] || [],
        summary: passengerSeat ? {} : values[4] || {},
        audit: values[5] || [],
      });
      setError("");
      setConnected(true);
    } catch (failure) {
      if (current !== generation.current) return;
      setError(failure.message);
      setConnected(false);
    } finally {
      if (current === generation.current) setLoading(false);
    }
  }, [token, flight, passengerSeat]);
  useEffect(() => {
    generation.current++;
    setData({
      tasks: [],
      announcements: [],
      inventory: [],
      audit: [],
      summary: {},
      context: {},
      profile: {},
      menu: [],
    });
    setLoading(true);
    if (!token) return;
    load();
    const controller = new AbortController();
    let retry;
    async function connect() {
      try {
        const response = await fetch("/api/events", {
          headers: { Authorization: `Bearer ${token}` },
          signal: controller.signal,
        });
        if (response.status === 401) {
          window.dispatchEvent(new Event("session-expired"));
          return;
        }
        if (!response.ok || !response.body)
          throw new Error("Stream unavailable");
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffered = "";
        while (!controller.signal.aborted) {
          const { value, done } = await reader.read();
          if (done) break;
          buffered += decoder.decode(value, { stream: true });
          const messages = buffered.split("\n\n");
          buffered = messages.pop();
          if (messages.some((message) => message.startsWith("data:"))) load();
        }
      } catch {
        if (!controller.signal.aborted) setConnected(false);
      }
      if (!controller.signal.aborted) retry = setTimeout(connect, 5000);
    }
    connect();
    const interval = setInterval(load, 15000);
    window.addEventListener("online", load);
    return () => {
      generation.current++;
      controller.abort();
      clearTimeout(retry);
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
        ignored: "Cancelled",
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
            {type === "crew" ? "CREW WORKSPACE" : "PASSENGER EXPERIENCE"}
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
                Your journey.
              </>
            )}
          </h1>
          <p>
            {type === "crew"
              ? "A clear view of every request, from acknowledgement to completion."
              : "Find something worth watching, plan your time, and connect with the cabin crew."}
          </p>
        </div>
        <span className="story-footer">
          Entertainment and cabin service, connected
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
                maxLength={4}
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
