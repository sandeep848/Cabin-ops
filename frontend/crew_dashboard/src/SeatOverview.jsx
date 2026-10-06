import { ACTIVE, label } from "../../shared/ui";

export default function SeatOverview({ profile, tasks, onSelect }) {
  if (!profile?.rows?.length)
    return (
      <section className="panel">
        <div className="section-heading">
          <h2>No aircraft layout configured</h2>
          <p>
            An operator must provision this flight's aircraft before service
            begins.
          </p>
        </div>
      </section>
    );
  return (
    <section className="panel cabin-panel">
      <div className="section-heading">
        <h2>{profile.aircraft_name}</h2>
        <p>
          {profile.seat_count} configured seats · {profile.origin} →{" "}
          {profile.destination}. Aisle spacing and seat letters follow the
          flight's layout snapshot.
        </p>
      </div>
      <div className="configured-seat-map">
        {profile.rows.map((row) => (
          <div key={row.row} className="configured-seat-row">
            <span className="row-label">{row.row}</span>
            {row.blocks.map((block, index) => (
              <div className="seat-block" key={index}>
                {block.split("").map((letter) => {
                  const seat = `${row.row}${letter}`;
                  const task = tasks
                    .filter(
                      (item) =>
                        item.seat === seat && ACTIVE.includes(item.status),
                    )
                    .sort(
                      (a, b) => (b.urgency === "high") - (a.urgency === "high"),
                    )[0];
                  return (
                    <button
                      key={seat}
                      disabled={!task}
                      aria-label={`Seat ${seat}, ${row.cabin}, ${label(row.zone)}${task ? ": " + label(task.intent) : ": no open requests"}`}
                      className={
                        task?.urgency === "high"
                          ? "seat-urgent"
                          : task
                            ? "seat-active"
                            : ""
                      }
                      onClick={() => onSelect(task)}
                    >
                      {letter}
                    </button>
                  );
                })}
              </div>
            ))}
            <span className="row-cabin">{row.cabin}</span>
          </div>
        ))}
      </div>
      <p className="muted">
        Highlighted seats have open requests. Red indicates urgent attention.
        Layouts support mixed cabins, omitted seat letters, and multiple aisles.
      </p>
    </section>
  );
}
