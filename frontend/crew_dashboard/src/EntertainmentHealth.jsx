import { useEffect, useState } from "react";
import { api, Notice } from "../../shared/ui";
export default function EntertainmentHealth({ token }) {
  const [data, setData] = useState(null),
    [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const next = await api("/experience/diagnostics", token);
        if (active) {
          setData(next);
          setError("");
        }
      } catch (failure) {
        if (active) setError(failure.message);
      }
    }
    load();
    const timer = setInterval(load, 30000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [token]);
  return (
    <section className="panel form-panel">
      <h2>Passenger entertainment health</h2>
      <Notice>{error}</Notice>
      {data ? (
        <>
          <p className="muted">
            Local media catalogue: {data.local_media.titles} titles.{" "}
            {data.local_media.verified
              ? "File integrity verified."
              : "File integrity needs attention."}
          </p>
          <dl className="health-summary">
            {["playing", "paused", "ended", "error"].map((state) => (
              <div key={state}>
                <dt>{state}</dt>
                <dd>{data.recent_terminals[state] || 0}</dd>
              </div>
            ))}
          </dl>
          <p className="muted">
            Browser-reported states within the last two minutes. This is not
            aircraft hardware telemetry. Passenger preferences and individual
            watched titles are not shown here.
          </p>
        </>
      ) : (
        <p role="status">Checking entertainment services…</p>
      )}
    </section>
  );
}
