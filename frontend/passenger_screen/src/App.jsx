import { useState, useEffect, useRef } from "react";
import {
  api,
  useCabinData,
  Login,
  Mark,
  Badge,
  Notice,
  Empty,
  label,
  time,
  BRAND,
} from "./ui";
import "./App.css";

const SERVICES = [
  {
    title: "Water",
    detail: "A glass of drinking water",
    text: "Could I get some water please?",
  },
  {
    title: "Comfort",
    detail: "An extra blanket",
    text: "Could I get an extra blanket please?",
  },
  {
    title: "Meal service",
    detail: "Ask about a meal",
    text: "Could I get a vegetarian meal please?",
  },
  {
    title: "Seat assistance",
    detail: "Help with your seat",
    text: "I need help adjusting my seat.",
  },
];
const URGENT =
  /emergency|fire|smoke|dizzy|pain|bleed|breath|faint|sick|allerg|chok|medical/i;

export default function App() {
  const [auth, setAuth] = useState(() =>
    JSON.parse(sessionStorage.getItem("cso-passenger") || "null"),
  );
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [receipt, setReceipt] = useState(null);
  const [section, setSection] = useState("service");
  const [online, setOnline] = useState(navigator.onLine);
  const [queued, setQueued] = useState([]);
  const [recording, setRecording] = useState(false);
  const recognition = useRef(null);
  const locked = useRef(false);
  const input = useRef(null);
  const data = useCabinData(auth?.token, auth?.flight_id, auth?.seat);
  const storageKey = auth ? `cso-outbox:${auth.flight_id}:${auth.seat}` : "";
  useEffect(() => {
    if (storageKey)
      setQueued(JSON.parse(sessionStorage.getItem(storageKey) || "[]"));
  }, [storageKey]);
  useEffect(() => {
    const changed = () => setOnline(navigator.onLine);
    const expired = () => logout();
    window.addEventListener("online", changed);
    window.addEventListener("offline", changed);
    window.addEventListener("session-expired", expired);
    return () => {
      window.removeEventListener("online", changed);
      window.removeEventListener("offline", changed);
      window.removeEventListener("session-expired", expired);
      recognition.current?.abort();
    };
  }, [storageKey]);
  function logout() {
    recognition.current?.abort();
    sessionStorage.removeItem("cso-passenger");
    if (storageKey) sessionStorage.removeItem(storageKey);
    setAuth(null);
    setQueued([]);
    setText("");
    setReceipt(null);
    setError("");
  }
  async function login(payload) {
    const result = await api("/auth/passenger", null, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    const next = { ...result, seat: payload.seat };
    sessionStorage.setItem("cso-passenger", JSON.stringify(next));
    setAuth(next);
  }
  function updateQueue(items) {
    setQueued(items);
    sessionStorage.setItem(storageKey, JSON.stringify(items));
  }
  async function deliver(item) {
    return api("/request", auth.token, {
      method: "POST",
      headers: { "Idempotency-Key": item.key },
      body: JSON.stringify(item.payload),
    });
  }
  async function submit(event) {
    event?.preventDefault();
    if (!text.trim() || locked.current) return;
    locked.current = true;
    setBusy(true);
    setError("");
    setReceipt(null);
    const item = {
      key: crypto.randomUUID(),
      payload: { seat: auth.seat, text: text.trim(), input_modality: "text" },
      created: new Date().toISOString(),
    };
    try {
      if (!navigator.onLine) throw new TypeError("Connection unavailable");
      const result = await deliver(item);
      setReceipt(result);
      setText("");
      await data.reload();
    } catch (failure) {
      if (failure instanceof TypeError || !navigator.onLine) {
        if (URGENT.test(item.payload.text))
          setError(
            "Delivery could not be confirmed. For urgent assistance, use the physical call button or speak directly to a crew member.",
          );
        else if (queued.length >= 20)
          setError(
            "Your saved request list is full. Connect and send or remove a saved request first.",
          );
        else {
          updateQueue([...queued, item]);
          setText("");
          setError(
            "Saved on this device. Your request has not been delivered. Send it when the connection returns.",
          );
        }
      } else setError(failure.message);
    } finally {
      locked.current = false;
      setBusy(false);
    }
  }
  async function sendQueued() {
    if (locked.current || !navigator.onLine) return;
    locked.current = true;
    setBusy(true);
    setError("");
    let remaining = [...queued];
    try {
      for (const item of queued) {
        await deliver(item);
        remaining = remaining.filter((entry) => entry.key !== item.key);
        updateQueue(remaining);
      }
      await data.reload();
    } catch (failure) {
      setError(`Some requests remain unsent. ${failure.message}`);
    } finally {
      locked.current = false;
      setBusy(false);
    }
  }
  function voice() {
    if (recording) {
      recognition.current?.stop();
      return;
    }
    const Recognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      setError(
        "Voice input is unavailable in this browser. Please type your request.",
      );
      return;
    }
    const engine = new Recognition();
    engine.lang = "en-US";
    engine.continuous = false;
    engine.interimResults = true;
    engine.onstart = () => setRecording(true);
    engine.onresult = (event) =>
      setText(
        Array.from(event.results)
          .map((result) => result[0].transcript)
          .join(" ")
          .slice(0, 500),
      );
    engine.onerror = () => {
      setError("Voice input could not be completed. Please type your request.");
      setRecording(false);
    };
    engine.onend = () => {
      setRecording(false);
      recognition.current = null;
    };
    recognition.current = engine;
    try {
      engine.start();
    } catch {
      setRecording(false);
      setError("Microphone could not start. Please type your request.");
    }
  }
  if (!auth) return <Login type="passenger" onLogin={login} />;
  const routinePaused =
    ["boarding", "taxi", "takeoff", "landing_preparation", "landing"].includes(
      data.context.flight_phase,
    ) || data.context.seatbelt_sign;
  return (
    <div className="passenger-app">
      <header className="passenger-header">
        <div className="brand">
          <Mark />
          <span>
            Cabin Service
            <br />
            <b>Operations</b>
          </span>
        </div>
        <div className="passenger-flight">
          <small>YOUR FLIGHT</small>
          <strong>{auth.flight_id}</strong>
        </div>
        <div className="seat-identity">
          <span>
            Seat <strong>{auth.seat}</strong>
          </span>
          <button className="text-button" onClick={logout}>
            Sign out
          </button>
        </div>
      </header>
      <main className="passenger-main">
        <div className="passenger-greeting">
          <div>
            <span className="eyebrow">WELCOME ABOARD</span>
            <h1>Make yourself comfortable.</h1>
            <p>Let us know what you need. We’ll keep you updated.</p>
          </div>
          <span className="connection">
            <i className={online && data.connected ? "connected" : ""} />
            {online && data.connected
              ? "Connected to cabin"
              : "Connection unavailable"}
          </span>
        </div>
        <nav className="passenger-tabs" aria-label="Passenger services">
          <button
            className={section === "service" ? "active" : ""}
            onClick={() => setSection("service")}
          >
            Your service
          </button>
          <button
            className={section === "announcements" ? "active" : ""}
            onClick={() => setSection("announcements")}
          >
            Announcements{" "}
            {data.announcements.length > 0 && (
              <span>{data.announcements.length}</span>
            )}
          </button>
        </nav>
        <Notice onDismiss={() => setError("")}>{error || data.error}</Notice>
        {routinePaused && (
          <div className="context-notice">
            Routine service is paused during the current flight conditions. You
            can still contact the crew directly.
          </div>
        )}
        {section === "service" ? (
          <>
            <section className="service-section">
              <div className="section-heading">
                <h2>A little help, whenever you need it.</h2>
                <p>Choose a service to prepare your request.</p>
              </div>
              <div className="service-grid">
                {SERVICES.map((service, index) => (
                  <button
                    key={service.title}
                    className="service-option"
                    disabled={busy}
                    onClick={() => {
                      setText(service.text);
                      setReceipt(null);
                      input.current?.focus();
                    }}
                  >
                    <span className="service-number">0{index + 1}</span>
                    <strong>{service.title}</strong>
                    <span>{service.detail}</span>
                    <span className="service-arrow" aria-hidden="true">
                      ↗
                    </span>
                  </button>
                ))}
              </div>
            </section>
            <div className="passenger-columns">
              <section className="panel request-compose">
                <span className="eyebrow">SOMETHING ELSE?</span>
                <h2>Tell us what you need.</h2>
                <form onSubmit={submit}>
                  <label htmlFor="service-request" className="sr-only">
                    Your service request
                  </label>
                  <textarea
                    ref={input}
                    id="service-request"
                    aria-label="Your service request"
                    placeholder="Write your request here…"
                    rows="4"
                    maxLength="500"
                    value={text}
                    onChange={(event) => setText(event.target.value)}
                    disabled={busy || recording}
                  />
                  <div className="compose-toolbar">
                    <button
                      className={recording ? "voice active" : "voice"}
                      type="button"
                      aria-pressed={recording}
                      disabled={busy}
                      onClick={voice}
                    >
                      {recording ? "Stop listening" : "Use voice"}
                    </button>
                    <small>{text.length} / 500</small>
                    <button
                      className="primary"
                      disabled={busy || recording || !text.trim()}
                    >
                      {busy
                        ? "Sending…"
                        : online
                          ? "Send request"
                          : "Save until connected"}
                    </button>
                  </div>
                </form>
                {receipt && (
                  <div className="receipt" role="status">
                    <strong>Request #{receipt.task_id} received</strong>
                    <Badge status={receipt.status} />
                    <p>{receipt.action}</p>
                  </div>
                )}
                <p className="assistance-note">
                  For urgent assistance, use the physical crew call button or
                  speak directly to a crew member.
                </p>
              </section>
              <section className="panel passenger-history">
                <div className="section-heading">
                  <h2>Your requests</h2>
                  <span>{data.tasks.length}</span>
                </div>
                {data.loading ? (
                  <p className="loading" role="status">
                    Loading your requests…
                  </p>
                ) : data.tasks.length ? (
                  <ol className="history-list">
                    {data.tasks.map((task) => (
                      <li key={task.id}>
                        <header>
                          <strong>{label(task.intent)}</strong>
                          <time>{time(task.created_at)}</time>
                        </header>
                        <Badge status={task.status} />
                        {task.status === "delayed" && (
                          <p>
                            Service is paused. The crew will review your request
                            when conditions allow.
                          </p>
                        )}
                        {task.status === "rejected" && <p>{task.action}</p>}
                        <small>Request #{task.id}</small>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <Empty
                    title="You're all set"
                    detail="Your requests and their progress will appear here."
                  />
                )}
              </section>
            </div>
            {queued.length > 0 && (
              <section className="panel outbox">
                <div className="section-heading">
                  <div>
                    <h2>Saved on this device</h2>
                    <p>
                      These requests have not yet been delivered. Review them
                      before sending.
                    </p>
                  </div>
                  <button
                    className="primary"
                    disabled={!online || busy}
                    onClick={sendQueued}
                  >
                    Send saved requests
                  </button>
                </div>
                <ul>
                  {queued.map((item) => (
                    <li key={item.key}>
                      <span>{item.payload.text}</span>
                      <button
                        className="text-button"
                        disabled={busy}
                        onClick={() =>
                          updateQueue(
                            queued.filter((entry) => entry.key !== item.key),
                          )
                        }
                      >
                        Remove
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </>
        ) : (
          <section className="panel passenger-announcements">
            <div className="section-heading">
              <h2>From the flight crew</h2>
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
                detail="Written updates from the flight crew will appear here."
              />
            )}
          </section>
        )}
        <footer className="workspace-footer">
          <span>{BRAND}</span>
          <span>
            Seat {auth.seat} · {label(data.context.flight_phase)}
          </span>
        </footer>
      </main>
    </div>
  );
}
