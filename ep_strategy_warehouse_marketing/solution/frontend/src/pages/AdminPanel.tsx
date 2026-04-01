import React, { useState, useEffect } from "react";
import "./AdminPanel.css";

interface ManualControl {
  scope_type: string;
  scope_key: string;
  is_paused: boolean;
  emergency_stop_active: boolean;
  emergency_mode: string | null;
  reason: string | null;
  updated_by: string | null;
  updated_at: string | null;
}

interface QueueItem {
  id: number;
  content_id: string;
  platform: string;
  status: string;
  content_data: any;
  scheduled_for: string;
  priority: number;
  retry_count: number;
  max_retries: number;
  last_error: string | null;
}

interface InterventionLog {
  id: number;
  action: string;
  scope_type: string;
  scope_key: string;
  actor: string;
  reason: string | null;
  created_at: string;
}

interface ControlStatus {
  global_control: ManualControl;
  platform_controls: ManualControl[];
  pending_approvals: number[];
  emergency_stop_active: boolean;
}

const AdminPanel: React.FC = () => {
  const [status, setStatus] = useState<ControlStatus | null>(null);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [logs, setLogs] = useState<InterventionLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const API_BASE = "http://127.0.0.1:8000/controls";

  const fetchData = async () => {
    try {
      const [statusRes, queueRes, logsRes] = await Promise.all([
        fetch(`${API_BASE}/status`),
        fetch(`${API_BASE}/queue`),
        fetch(`${API_BASE}/interventions`)
      ]);

      if (!statusRes.ok || !queueRes.ok || !logsRes.ok) {
        throw new Error("Failed to fetch data from backend");
      }

      const statusData = await statusRes.json();
      const queueData = await queueRes.json();
      const logsData = await logsRes.json();

      setStatus(statusData);
      setQueue(queueData);
      setLogs(logsData);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleGlobalPause = async (paused: boolean) => {
    try {
      const res = await fetch(`${API_BASE}/pause/global`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          actor: "Operator",
          paused,
          reason: paused ? "Manual intervention" : "Resuming operations"
        })
      });
      if (res.ok) fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  const handlePlatformPause = async (platform: string, paused: boolean) => {
    try {
      const res = await fetch(`${API_BASE}/pause/platform/${platform}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          actor: "Operator",
          paused,
          reason: paused ? `Pausing ${platform}` : `Resuming ${platform}`
        })
      });
      if (res.ok) fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  const handleEmergencyStop = async (mode: "freeze" | "clear") => {
    if (!window.confirm(`Are you sure you want to trigger EMERGENCY STOP (${mode})?`)) return;
    try {
      const res = await fetch(`${API_BASE}/emergency-stop`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          actor: "Operator",
          mode,
          reason: "EMERGENCY INTERVENTION"
        })
      });
      if (res.ok) fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  const handleQueueAction = async (id: number, action: "approve" | "reject") => {
    try {
      const res = await fetch(`${API_BASE}/queue/${id}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          actor: "Operator",
          reason: `Manual ${action}`
        })
      });
      if (res.ok) fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  if (loading && !status) return <div className="admin-loading">Loading Admin Panel...</div>;
  if (error) return <div className="admin-error">Error: {error}</div>;

  return (
    <div className="admin-panel">
      <header className="admin-header">
        <h1>Marketing Engine Control</h1>
        <div className="global-actions">
          {status?.global_control.is_paused ? (
            <button className="btn btn-resume" onClick={() => handleGlobalPause(false)}>Resume Global</button>
          ) : (
            <button className="btn btn-pause" onClick={() => handleGlobalPause(true)}>Pause Global</button>
          )}
          <button className="btn btn-emergency" onClick={() => handleEmergencyStop("freeze")}>EMERGENCY STOP</button>
        </div>
      </header>

      <section className="admin-section">
        <h2>Platform Controls</h2>
        <div className="platform-grid">
          {status?.platform_controls.map(ctrl => (
            <div key={ctrl.scope_key} className={`platform-card ${ctrl.is_paused ? "paused" : "active"}`}>
              <h3>{ctrl.scope_key.toUpperCase()}</h3>
              <p>Status: {ctrl.is_paused ? "Paused" : "Active"}</p>
              <button 
                className={`btn ${ctrl.is_paused ? "btn-resume" : "btn-pause"}`}
                onClick={() => handlePlatformPause(ctrl.scope_key, !ctrl.is_paused)}
              >
                {ctrl.is_paused ? "Resume" : "Pause"}
              </button>
            </div>
          ))}
        </div>
      </section>

      <section className="admin-section">
        <h2>Content Queue</h2>
        <table className="queue-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Platform</th>
              <th>Status</th>
              <th>Scheduled For</th>
              <th>Priority</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {queue.map(item => (
              <tr key={item.id} className={`status-${item.status}`}>
                <td>{item.id}</td>
                <td>{item.platform}</td>
                <td><span className="status-badge">{item.status}</span></td>
                <td>{new Date(item.scheduled_for).toLocaleString()}</td>
                <td>{item.priority}</td>
                <td>
                  {item.status === "approval_pending" && (
                    <div className="cell-actions">
                      <button className="btn-sm btn-approve" onClick={() => handleQueueAction(item.id, "approve")}>Approve</button>
                      <button className="btn-sm btn-reject" onClick={() => handleQueueAction(item.id, "reject")}>Reject</button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
            {queue.length === 0 && <tr><td colSpan={6}>Queue is empty</td></tr>}
          </tbody>
        </table>
      </section>

      <section className="admin-section">
        <h2>Recent Interventions</h2>
        <div className="log-list">
          {logs.slice(0, 10).map(log => (
            <div key={log.id} className="log-item">
              <span className="log-date">{new Date(log.created_at).toLocaleString()}</span>
              <span className="log-actor">{log.actor}</span>
              <span className="log-action">{log.action}</span>
              <span className="log-scope">{log.scope_type}:{log.scope_key}</span>
              <span className="log-reason">{log.reason}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};

export default AdminPanel;
