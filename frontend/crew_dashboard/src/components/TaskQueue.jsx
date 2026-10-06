import React from 'react';
import { getIntentLabel, ZONE_LABELS, formatTime } from './Helpers';

const resolvedLabel = (status) => {
  if (status === 'completed') return 'Fulfilled';
  if (status === 'answered')  return 'Answered';
  if (status === 'rejected' || status === 'delayed' || status === 'ignored') return 'Unavailable';
  return status;
};

export default function TaskQueue({
  activeTasks,
  resolvedTasks,
  groupedActive,
  activeTab,
  setActiveTab,
  isRestricted,
  actionLoading,
  acceptTask,
  completeTask,
}) {
  return (
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

              const isEmergency = task.intent === 'emergency' || task.intent === 'medical_assistance' || task.intent === 'allergy_question';
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
                    ) : (task.status === 'pending' || task.status === 'urgent_pending' || task.status === 'delayed') ? (
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
  );
}
