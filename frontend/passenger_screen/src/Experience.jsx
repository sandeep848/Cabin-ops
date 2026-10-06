import { useEffect, useRef, useState } from "react";
import { api } from "../../shared/ui";

export const length = (seconds) =>
  `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
export const INTERESTS = [
  "science",
  "travel",
  "art",
  "music",
  "calm",
  "learning",
  "culture",
];
export const DEFAULTS = {
  interests: [],
  mood: "any",
  kind: "all",
  captions_required: true,
  available_minutes: 10,
  limit: 8,
};

export function ContentCard({ item, onPlay, progress }) {
  return (
    <article className="content-card">
      <button
        className="poster-button"
        onClick={() => onPlay(item)}
        aria-label={`Play ${item.title}`}
      >
        <img src={item.poster_url} alt="" loading="lazy" />
        <span className="play-label" aria-hidden="true">
          {item.kind === "audio" ? "Listen" : "Watch"} ↗
        </span>
        <span className="duration">{length(item.duration_seconds)}</span>
      </button>
      <div className="content-copy">
        <span className="media-kind">
          {item.genre} · {item.kind === "video" ? "CC" : "Audio"}
        </span>
        <h3>{item.title}</h3>
        <p>{item.description}</p>
        {progress > 0 && progress < item.duration_seconds - 2 && (
          <span className="resume-label">Resume at {length(progress)}</span>
        )}
        {item.reasons && (
          <details>
            <summary>Why this pick?</summary>
            <ul>
              {item.reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          </details>
        )}
      </div>
    </article>
  );
}

export function Preferences({ value, onChange, embedded = false }) {
  const patch = (update) => onChange({ ...value, ...update });
  return (
    <div
      className={
        embedded ? "preference-form compact-preferences" : "preference-form"
      }
    >
      <fieldset>
        <legend>What interests you?</legend>
        <div className="interest-chips">
          {INTERESTS.map((interest) => (
            <button
              key={interest}
              type="button"
              aria-pressed={value.interests.includes(interest)}
              onClick={() =>
                patch({
                  interests: value.interests.includes(interest)
                    ? value.interests.filter((tag) => tag !== interest)
                    : [...value.interests, interest],
                })
              }
            >
              {interest}
            </button>
          ))}
        </div>
      </fieldset>
      <div className="preference-controls">
        <label>
          Pace
          <select
            value={value.mood}
            onChange={(event) => patch({ mood: event.target.value })}
          >
            <option value="any">Any pace</option>
            <option value="slow">Slow down</option>
            <option value="curious">Explore</option>
            <option value="energetic">Something lively</option>
          </select>
        </label>
        <label>
          Time available (minutes)
          <input
            type="number"
            min="0"
            max="180"
            value={value.available_minutes}
            onChange={(event) =>
              patch({
                available_minutes: Math.min(
                  180,
                  Math.max(0, Number(event.target.value)),
                ),
              })
            }
          />
        </label>
      </div>
      <p className="privacy-copy">
        Optional preferences stay in memory on this screen and are sent only to
        the onboard ranking service. They are not saved by the server.
      </p>
    </div>
  );
}

export function Journey({
  token,
  preferences,
  onChange,
  onPlay,
  context,
  onError,
}) {
  const [plan, setPlan] = useState(null);
  const [busy, setBusy] = useState(false);
  const [minutesAtBuild, setMinutesAtBuild] = useState(null);
  async function build() {
    setBusy(true);
    try {
      const result = await api("/experience/plan", token, {
        method: "POST",
        body: JSON.stringify(preferences),
      });
      setPlan(result);
      setMinutesAtBuild(context.minutes_to_landing);
    } catch (error) {
      onError(error.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="journey-view">
      <div className="view-title">
        <span className="kicker">MAKE THE MOST OF YOUR FLIGHT</span>
        <h1>A little time, well spent.</h1>
        <p>
          Build a short playlist around your interests. We leave five minutes
          before the crew’s current landing estimate.
        </p>
      </div>
      <div className="journey-grid">
        <section className="atlas-panel">
          <h2>Your time on board</h2>
          <Preferences
            value={preferences}
            onChange={(next) => {
              onChange(next);
              setPlan(null);
            }}
          />
          <button className="atlas-primary" disabled={busy} onClick={build}>
            {busy ? "Planning…" : "Build my journey"}
          </button>
        </section>
        <section className="atlas-panel">
          <span className="kicker">YOUR PLAYLIST</span>
          <h2>
            {plan?.items.length
              ? `${length(plan.total_seconds)} of discovery`
              : "A plan that fits your time"}
          </h2>
          {plan && minutesAtBuild !== context.minutes_to_landing && (
            <p role="status">
              Flight timing changed. Rebuild your plan for the latest estimate.
            </p>
          )}
          {plan?.items.length ? (
            <>
              <ol className="plan-list">
                {plan.items.map((item, index) => (
                  <li key={item.id}>
                    <span>{String(index + 1).padStart(2, "0")}</span>
                    <div>
                      <h3>{item.title}</h3>
                      <p>
                        {item.kind} · {length(item.duration_seconds)}
                      </p>
                    </div>
                    <button
                      className="atlas-secondary"
                      onClick={() => onPlay(item)}
                      aria-label={`Play ${item.title}`}
                    >
                      Play
                    </button>
                  </li>
                ))}
              </ol>
              <p className="privacy-copy">
                Includes 15-second transitions. {length(plan.remaining_seconds)}{" "}
                remains in your chosen window. Start each title when you are
                ready.
              </p>
            </>
          ) : (
            <p className="empty-plan">
              {plan
                ? "No titles fit this window. Try a longer window or wait for an updated landing estimate."
                : "Choose a pace and your interests, then build your journey. Each recommendation includes a reason."}
            </p>
          )}
        </section>
      </div>
    </section>
  );
}

export function Player({
  item,
  token,
  progress,
  announcement,
  onClose,
  onProgress,
  onError,
}) {
  const element = useRef(null);
  const dialog = useRef(null);
  const initialAnnouncement = useRef(announcement?.id);
  const [interruption, setInterruption] = useState(null);
  const [remember, setRemember] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");
  const [playing, setPlaying] = useState(false);
  useEffect(() => {
    const previous = document.activeElement;
    dialog.current?.querySelector("button")?.focus();
    const keyboard = (event) => {
      if (event.key === "Escape") onClose();
      if (event.key === "Tab") {
        const controls = [
          ...dialog.current.querySelectorAll(
            "button:not(:disabled), input, video, audio, summary",
          ),
        ];
        const first = controls[0],
          last = controls.at(-1);
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", keyboard);
    return () => {
      element.current?.pause();
      document.body.style.overflow = overflow;
      window.removeEventListener("keydown", keyboard);
      previous?.focus();
    };
  }, []);
  useEffect(() => {
    if (announcement?.id && announcement.id !== initialAnnouncement.current) {
      initialAnnouncement.current = announcement.id;
      element.current?.pause();
      setInterruption(announcement);
    }
  }, [announcement]);
  async function health(state) {
    try {
      await api("/experience/playback-health", token, {
        method: "POST",
        body: JSON.stringify({ state, content_id: item.id }),
      });
    } catch {
      /* Device health is best effort; it never blocks playback. */
    }
  }
  async function save() {
    const seconds = Math.min(
      item.duration_seconds,
      Math.max(0, element.current?.currentTime || 0),
    );
    try {
      await api(`/experience/progress/${item.id}`, token, {
        method: "PUT",
        body: JSON.stringify({ position_seconds: seconds }),
      });
      onProgress(item.id, seconds);
      setSaveMessage("Playback position saved for this seat.");
    } catch (error) {
      onError(error.message);
    }
  }
  const props = {
    ref: element,
    src: item.media_url,
    controls: true,
    preload: "metadata",
    onLoadedMetadata: () => {
      if (progress && progress < item.duration_seconds - 2)
        element.current.currentTime = progress;
    },
    onPlay: () => {
      if (interruption) {
        element.current?.pause();
        return;
      }
      setPlaying(true);
      health("playing");
    },
    onPause: () => {
      setPlaying(false);
      if (remember) save();
      health("paused");
    },
    onEnded: () => {
      setPlaying(false);
      if (remember) save();
      health("ended");
    },
    onError: () => {
      health("error");
      onError(
        "This title could not play. Reconnect to the cabin network and reopen it.",
      );
    },
    "aria-label": item.title,
  };
  return (
    <div className="player-backdrop">
      <section
        ref={dialog}
        className="atlas-player"
        role="dialog"
        aria-modal="true"
        aria-label={`Playing ${item.title}`}
      >
        <header>
          <div>
            <span className="kicker">ONBOARD LIBRARY</span>
            <h2>{item.title}</h2>
          </div>
          <button className="atlas-secondary" onClick={onClose}>
            Close player
          </button>
        </header>
        {item.kind === "video" ? (
          <video {...props} poster={item.poster_url}>
            <track
              kind="captions"
              src={item.captions_url}
              srcLang={item.language}
              label={
                { en: "English", de: "Deutsch", hi: "Hindi" }[item.language] ||
                item.language
              }
              default
            />
          </video>
        ) : (
          <div className="audio-stage">
            <img src={item.poster_url} alt="" />
            <audio {...props} />
          </div>
        )}
        {interruption && (
          <div className="player-interruption" role="alert">
            <span className="kicker">FROM THE CABIN CREW</span>
            <h3>{interruption.speaker}</h3>
            <p>{interruption.text}</p>
            <button
              className="atlas-primary"
              onClick={() => setInterruption(null)}
            >
              I’ve read the announcement
            </button>
            <p className="privacy-copy">
              Playback is paused. Use the player controls when you are ready to
              continue.
            </p>
          </div>
        )}
        <div className="player-details">
          <p>{item.description}</p>
          <label className="remember-choice">
            <input
              type="checkbox"
              checked={remember}
              onChange={(event) => setRemember(event.target.checked)}
            />
            Save my position when I pause
          </label>
          <button
            className="atlas-secondary"
            disabled={!remember}
            onClick={save}
          >
            Save position now
          </button>
          <p role="status">{saveMessage}</p>
          <p className="privacy-copy">
            {playing
              ? "Playing locally on the cabin network."
              : "Press play when you are ready."}{" "}
            {item.license === "CC0-1.0"
              ? "This original title is released under CC0."
              : `Content license: ${item.license}. Rights are managed by the operator.`}
          </p>
        </div>
      </section>
    </div>
  );
}
