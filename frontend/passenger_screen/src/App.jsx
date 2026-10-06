import { useEffect, useRef, useState } from "react";
import { api, useCabinData, Login, Notice, label } from "../../shared/ui";
import Services from "./Services";
import {
  ContentCard,
  Preferences,
  Journey,
  Player,
  DEFAULTS,
  length,
} from "./Experience";
import "./App.css";

const NAV = [
  "Discover",
  "Watch",
  "Listen",
  "My journey",
  "Flight",
  "Cabin service",
  "Settings",
];

export default function App() {
  const [auth, setAuth] = useState(null);
  const [view, setView] = useState("Discover");
  const [catalog, setCatalog] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [preferences, setPreferences] = useState(DEFAULTS);
  const [progress, setProgress] = useState({});
  const [player, setPlayer] = useState(null);
  const [error, setError] = useState("");
  const [mediaReady, setMediaReady] = useState(false);
  const [search, setSearch] = useState("");
  const [largeText, setLargeText] = useState(false);
  const [contrast, setContrast] = useState(false);
  const [reduceMotion, setReduceMotion] = useState(false);
  const [message, setMessage] = useState("");
  const data = useCabinData(auth?.token, auth?.flight_id, auth?.seat);
  const generation = useRef(0);
  async function logout() {
    const token = auth?.token;
    generation.current++;
    if (auth)
      sessionStorage.removeItem(`cso-outbox:${auth.flight_id}:${auth.seat}`);
    sessionStorage.removeItem("cso-passenger");
    setAuth(null);
    setPlayer(null);
    setCatalog([]);
    setProgress({});
    setRecommendations([]);
    setPreferences(DEFAULTS);
    setMediaReady(false);
    setError("");
    setView("Discover");
    setLargeText(false);
    setContrast(false);
    setMessage("");
    setReduceMotion(false);
    if (token) {
      try {
        await api("/auth/logout", token, { method: "POST" });
      } catch {
        /* Local credentials are already erased. The server session expires in six hours. */
      }
    }
  }
  useEffect(() => {
    const expired = () => logout();
    window.addEventListener("session-expired", expired);
    return () => window.removeEventListener("session-expired", expired);
  }, [auth]);
  async function login(payload) {
    const result = await api("/auth/passenger", null, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    // Bearer access is memory-only: a shared screen never retains it across reloads.
    setAuth({ ...result, seat: payload.seat });
  }
  useEffect(() => {
    if (!auth) return;
    let active = true;
    async function bootstrap() {
      try {
        await api("/experience/media-session", auth.token, { method: "POST" });
        const [listing, positions] = await Promise.all([
          api("/experience/catalog", auth.token),
          api("/experience/progress", auth.token),
        ]);
        if (active) {
          setCatalog(listing.items);
          setProgress(
            Object.fromEntries(
              positions.map((row) => [row.content_id, row.position_seconds]),
            ),
          );
          setMediaReady(true);
        }
      } catch (failure) {
        if (active) setError(failure.message);
      }
    }
    bootstrap();
    const refresh = setInterval(
      () =>
        api("/experience/media-session", auth.token, { method: "POST" }).catch(
          () => {},
        ),
      600000,
    );
    return () => {
      active = false;
      clearInterval(refresh);
    };
  }, [auth]);
  useEffect(() => {
    if (!auth || !mediaReady) return;
    const current = ++generation.current;
    const debounce = setTimeout(async () => {
      try {
        const result = await api("/experience/recommendations", auth.token, {
          method: "POST",
          body: JSON.stringify(preferences),
        });
        if (current === generation.current) setRecommendations(result.items);
      } catch (failure) {
        if (current === generation.current) setError(failure.message);
      }
    }, 300);
    return () => clearTimeout(debounce);
  }, [auth, mediaReady, preferences, data.context.minutes_to_landing]);
  async function open(item) {
    try {
      await api("/experience/media-session", auth.token, { method: "POST" });
      setPlayer(item);
      setError("");
    } catch (failure) {
      setError(failure.message);
    }
  }
  async function forget() {
    try {
      await api("/experience/history", auth.token, { method: "DELETE" });
      setProgress({});
      setPreferences(DEFAULTS);
      setMessage(
        "Your playback positions and current preferences have been cleared.",
      );
    } catch (failure) {
      setError(failure.message);
    }
  }
  if (!auth) return <Login type="passenger" onLogin={login} />;
  const visible = catalog.filter(
    (item) =>
      (view === "Watch"
        ? item.kind === "video"
        : view === "Listen"
          ? item.kind === "audio"
          : true) &&
      `${item.title} ${item.genre} ${item.description}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  const feature =
    recommendations.find((item) => item.kind === "video") ||
    catalog.find((item) => item.kind === "video") ||
    catalog[0];
  const latest = data.announcements[0];
  return (
    <div
      className={`atlas ${largeText ? "atlas-large" : ""} ${contrast ? "atlas-contrast" : ""} ${reduceMotion ? "atlas-still" : ""}`}
    >
      <a href="#atlas-main" className="skip-link">
        Skip to content
      </a>
      <header className="atlas-header">
        <button
          className="atlas-brand"
          onClick={() => setView("Discover")}
          aria-label="Cabin Atlas home"
        >
          <span className="atlas-symbol" aria-hidden="true">
            A
          </span>
          <span>
            Cabin Atlas<small>YOUR TIME ABOVE</small>
          </span>
        </button>
        <div className="atlas-flight-id">
          <span>
            {data.profile?.origin} → {data.profile?.destination}
          </span>
          <span>
            Seat <b>{auth.seat}</b>
          </span>
          <button className="atlas-link" onClick={logout}>
            Sign out
          </button>
        </div>
      </header>
      <nav className="atlas-nav" aria-label="Onboard experience">
        {NAV.map((name) => (
          <button
            key={name}
            aria-current={view === name ? "page" : undefined}
            className={view === name ? "active" : ""}
            onClick={() => {
              setView(name);
              setSearch("");
              setError("");
            }}
          >
            {name}
          </button>
        ))}
      </nav>
      <main id="atlas-main" tabIndex="-1" className="atlas-main">
        <Notice onDismiss={() => setError("")}>{error || data.error}</Notice>
        {view === "Discover" && (
          <>
            <section className="discovery-hero">
              <div className="hero-copy">
                <span className="kicker">WELCOME TO YOUR SEAT</span>
                <h1>
                  A different
                  <br />
                  point of view.
                </h1>
                <p>
                  Small discoveries. A quieter soundtrack.
                  <br />A little space to enjoy the journey.
                </p>
                <div className="hero-actions">
                  <button
                    className="atlas-primary"
                    disabled={!feature || !mediaReady}
                    onClick={() => open(feature)}
                  >
                    {feature
                      ? `Explore ${feature.title.toLowerCase()}`
                      : "Browse the onboard library"}{" "}
                    <span aria-hidden="true">↗</span>
                  </button>
                  <button
                    className="atlas-link"
                    onClick={() => setView("My journey")}
                  >
                    Plan my time →
                  </button>
                </div>
                <div className="hero-flight">
                  <span>
                    {data.context.minutes_to_landing ?? "—"}
                    <small>MIN TO LANDING</small>
                  </span>
                  <span>
                    {label(data.context.flight_phase)}
                    <small>FROM THE CABIN CREW</small>
                  </span>
                </div>
              </div>
              <div className="hero-art">
                {feature && <img src={feature.poster_url} alt="" />}
                <span className="hero-art-caption">
                  {feature?.title}{" "}
                  <span>
                    {feature
                      ? `${feature.kind.toUpperCase()} · ${length(feature.duration_seconds)}`
                      : ""}
                  </span>
                </span>
              </div>
            </section>
            <section className="recommendation-section">
              <div className="atlas-section-heading">
                <div>
                  <span className="kicker">A GOOD PLACE TO START</span>
                  <h2>For your time on board</h2>
                </div>
                <button
                  className="atlas-link"
                  onClick={() => setView("Settings")}
                >
                  Choose your interests →
                </button>
              </div>
              {!mediaReady ? (
                <p role="status">Connecting to your onboard library…</p>
              ) : recommendations.length ? (
                <div className="content-grid">
                  {recommendations.slice(0, 4).map((item) => (
                    <ContentCard
                      key={item.id}
                      item={item}
                      onPlay={open}
                      progress={progress[item.id]}
                    />
                  ))}
                </div>
              ) : (
                <p className="atlas-empty">
                  No titles fit the current time window. Browse the library or
                  update your time preference.
                </p>
              )}
            </section>
            <section className="discovery-bottom">
              <button onClick={() => setView("Cabin service")}>
                <span className="kicker">AN ATTENTIVE CABIN</span>
                <h2>A little help, at your seat.</h2>
                <p>Refreshments, comfort and a clear view of your requests.</p>
                <span>Open cabin service →</span>
              </button>
              <button onClick={() => setView("Flight")}>
                <span className="kicker">FOLLOW YOUR FLIGHT</span>
                <h2>Your journey, at a glance.</h2>
                <p>Cabin conditions and the latest written crew updates.</p>
                <span>Flight overview →</span>
              </button>
            </section>
          </>
        )}
        {["Watch", "Listen"].includes(view) && (
          <section>
            <div className="view-title">
              <span className="kicker">ONBOARD LIBRARY</span>
              <h1>
                {view === "Watch"
                  ? "A few minutes elsewhere."
                  : "Find your soundtrack."}
              </h1>
              <p>
                {view === "Watch"
                  ? "Short discoveries and visual essays. Caption tracks are shown in the player."
                  : "Your onboard soundtrack, available on the cabin network."}
              </p>
            </div>
            <div className="library-tools">
              <label className="sr-only" htmlFor="library-search">
                Search onboard content
              </label>
              <input
                id="library-search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search titles or interests"
              />
              <span>{visible.length} titles · local playback</span>
            </div>
            <div className="content-grid library-grid">
              {visible.map((item) => (
                <ContentCard
                  key={item.id}
                  item={item}
                  onPlay={open}
                  progress={progress[item.id]}
                />
              ))}
            </div>
            {!visible.length && (
              <p className="atlas-empty">No titles match your search.</p>
            )}
          </section>
        )}
        {view === "My journey" && (
          <Journey
            token={auth.token}
            preferences={preferences}
            onChange={setPreferences}
            onPlay={open}
            context={data.context}
            onError={setError}
          />
        )}
        {view === "Flight" && (
          <section>
            <div className="view-title">
              <span className="kicker">
                ON BOARD {auth.flight_id} · {data.profile?.origin} →{" "}
                {data.profile?.destination}
              </span>
              <h1>Here, above it all.</h1>
              <p>Current estimates and written updates from the cabin crew.</p>
            </div>
            <div className="flight-overview">
              <div className="flight-time">
                <span className="kicker">ESTIMATED TIME TO LANDING</span>
                <strong>
                  {data.context.minutes_to_landing ?? "—"}
                  <small>minutes</small>
                </strong>
                <p>Manually maintained by the cabin crew.</p>
                <svg viewBox="0 0 600 110" aria-hidden="true">
                  <path
                    d="M20 95Q300 -60 580 95"
                    stroke="currentColor"
                    strokeWidth="2"
                    fill="none"
                    strokeDasharray="6 8"
                  />
                  <circle cx="20" cy="95" r="5" fill="currentColor" />
                  <circle cx="580" cy="95" r="5" fill="currentColor" />
                </svg>
              </div>
              <dl className="flight-conditions">
                <div>
                  <dt>Flight phase</dt>
                  <dd>{label(data.context.flight_phase)}</dd>
                </div>
                <div>
                  <dt>Seatbelt sign</dt>
                  <dd>{data.context.seatbelt_sign ? "On" : "Off"}</dd>
                </div>
                <div>
                  <dt>Meal service</dt>
                  <dd>
                    {data.context.meal_service_active ? "Active" : "Not active"}
                  </dd>
                </div>
                <div>
                  <dt>Your seat</dt>
                  <dd>{auth.seat}</dd>
                </div>
              </dl>
            </div>
            <div className="atlas-section-heading">
              <h2>From the flight crew</h2>
              <span>{data.announcements.length} updates</span>
            </div>
            <div className="flight-announcements">
              {data.announcements.length ? (
                data.announcements.map((item) => (
                  <article key={item.id}>
                    <span className="kicker">
                      {item.speaker} ·{" "}
                      {new Date(item.timestamp).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                    <p>{item.text}</p>
                  </article>
                ))
              ) : (
                <p>
                  No written updates yet. Always follow the crew’s spoken
                  instructions.
                </p>
              )}
            </div>
          </section>
        )}
        {view === "Cabin service" && (
          <>
            <div className="view-title">
              <span className="kicker">HERE WHEN YOU NEED US</span>
              <h1>A more comfortable journey.</h1>
              <p>
                For urgent assistance, use the physical call button or speak to
                a crew member.
              </p>
            </div>
            <Services auth={auth} data={data} />
          </>
        )}
        {view === "Settings" && (
          <section>
            <div className="view-title">
              <span className="kicker">MAKE THIS SPACE YOURS</span>
              <h1>Your screen. Your choices.</h1>
              <p>
                Set your interests, adjust the display, or clear your saved
                playback positions.
              </p>
            </div>
            <div className="settings-grid">
              <section className="atlas-panel">
                <h2>Personal recommendations</h2>
                <Preferences value={preferences} onChange={setPreferences} />
              </section>
              <section className="atlas-panel">
                <h2>Screen & privacy</h2>
                <div className="display-options">
                  <label>
                    <input
                      type="checkbox"
                      checked={largeText}
                      onChange={(event) => setLargeText(event.target.checked)}
                    />
                    Larger text
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={contrast}
                      onChange={(event) => setContrast(event.target.checked)}
                    />
                    Higher contrast
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={reduceMotion}
                      onChange={(event) =>
                        setReduceMotion(event.target.checked)
                      }
                    />
                    Reduce motion
                  </label>
                </div>
                <h3>Your playback history</h3>
                <p className="privacy-copy">
                  Playback positions are saved only when you choose to save them
                  in the player. Clearing them does not delete service requests
                  required for cabin operations.
                </p>
                <button className="atlas-secondary" onClick={forget}>
                  Clear my playback history
                </button>
                <p role="status">{message}</p>
              </section>
            </div>
          </section>
        )}
        <footer className="atlas-footer">
          <span>Cabin Atlas · Onboard experience</span>
          <span>
            <i className={data.connected ? "online-dot" : "offline-dot"} />
            {data.connected
              ? "Cabin network connected"
              : "Cabin connection unavailable"}
          </span>
        </footer>
      </main>
      {player && (
        <Player
          key={player.id}
          item={player}
          token={auth.token}
          progress={progress[player.id]}
          announcement={latest}
          onClose={() => setPlayer(null)}
          onProgress={(id, position) =>
            setProgress((current) => ({ ...current, [id]: position }))
          }
          onError={setError}
        />
      )}
    </div>
  );
}
