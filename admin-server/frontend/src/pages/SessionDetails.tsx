import React, { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import {
  Layers,
  ArrowLeft,
  Monitor,
  FileCode,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { sessionApi } from "../services/sessionApi";
import type { SessionDetail } from "../types";

import { SessionTimeline } from "../components/sessions/SessionTimeline";
import { LoadingState } from "../components/common/LoadingState";
import { ErrorState } from "../components/common/ErrorState";

export const SessionDetails: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [session, setSession] = useState<SessionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showRawJson, setShowRawJson] = useState(false);
  const [copied, setCopied] = useState(false);

  const loadSession = async () => {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await sessionApi.getSessionById(sessionId);
      setSession(data);
    } catch (err: any) {
      setError(err.message || "Failed to load session details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSession();
  }, [sessionId]);

  if (loading) return <LoadingState message="Retrieving session package & telemetry..." />;
  if (error || !session) return <ErrorState message={error || "Session not found."} onRetry={loadSession} />;

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(session, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const events = Array.isArray(session.events)
    ? session.events
    : Array.isArray((session as any).session?.events)
    ? (session as any).session.events
    : [];

  const focusSummary =
    session.focus_summary && typeof session.focus_summary === "object"
      ? session.focus_summary
      : {};

  return (
    <div style={{ padding: "28px", display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Back Button */}
      <div>
        <Link
          to="/sessions"
          className="apple-btn apple-btn-secondary"
          style={{ display: "inline-flex", fontSize: "0.78rem", marginBottom: "14px" }}
        >
          <ArrowLeft size={13} />
          <span>Back to Sessions</span>
        </Link>

        {/* Session Header Card */}
        <div className="glass-panel" style={{ padding: "24px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px" }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span className="badge badge-blue">
                  <Layers size={12} />
                  Session Package
                </span>
                <span style={{ fontFamily: "monospace", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                  {session.session_id}
                </span>
              </div>
              <h1 style={{ fontSize: "1.35rem", fontWeight: 700, marginTop: "6px" }}>
                <Link to={`/employees/${session.employee_id}`} style={{ color: "var(--text-primary)", textDecoration: "none" }}>
                  {session.employee_name}
                </Link>
              </h1>
              <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "2px" }}>
                Device ID: <code style={{ fontFamily: "monospace" }}>{session.employee_id}</code>
                {session.metadata?.os && ` • ${session.metadata.os}`}
              </p>
            </div>

            {/* Timings */}
            <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
              <div style={{ padding: "10px 16px", borderRadius: "var(--radius-md)", backgroundColor: "var(--system-grouped-bg)", textAlign: "center" }}>
                <div style={{ fontSize: "0.7rem", color: "var(--text-tertiary)", fontWeight: 600 }}>DURATION</div>
                <div style={{ fontSize: "1.15rem", fontWeight: 700 }}>{formatDuration(session.duration_seconds)}</div>
              </div>
              <div style={{ padding: "10px 16px", borderRadius: "var(--radius-md)", backgroundColor: "var(--system-grouped-bg)", textAlign: "center" }}>
                <div style={{ fontSize: "0.7rem", color: "var(--text-tertiary)", fontWeight: 600 }}>START TIME</div>
                <div style={{ fontSize: "0.95rem", fontWeight: 600 }}>
                  {new Date(session.start_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                </div>
              </div>
              <div style={{ padding: "10px 16px", borderRadius: "var(--radius-md)", backgroundColor: "var(--system-grouped-bg)", textAlign: "center" }}>
                <div style={{ fontSize: "0.7rem", color: "var(--text-tertiary)", fontWeight: 600 }}>END TIME</div>
                <div style={{ fontSize: "0.95rem", fontWeight: 600 }}>
                  {new Date(session.end_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Application Focus Summary & Event Timeline */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
          gap: "20px",
        }}
      >
        {/* Application Focus Summary */}
        <div className="glass-panel" style={{ padding: "24px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
            <div>
              <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>Application Focus Summary</h3>
              <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)" }}>
                Aggregated active seconds per binary
              </p>
            </div>
            <span className="badge badge-gray">{Object.keys(focusSummary).length} Apps</span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {Object.keys(focusSummary).length === 0 ? (
              <div style={{ padding: "20px", color: "var(--text-tertiary)", fontSize: "0.85rem" }}>
                No discrete application durations recorded.
              </div>
            ) : (
              Object.entries(focusSummary).map(([app, seconds]) => (
                <div
                  key={app}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "10px 14px",
                    borderRadius: "var(--radius-md)",
                    backgroundColor: "var(--system-grouped-bg)",
                    border: "1px solid var(--border-subtle)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <Monitor size={16} color="var(--apple-blue)" />
                    <span style={{ fontWeight: 600, fontSize: "0.85rem", fontFamily: "monospace" }}>
                      {app}
                    </span>
                  </div>
                  <span className="badge badge-blue" style={{ fontSize: "0.78rem" }}>
                    {Math.round(seconds)} sec
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Human-Readable Event Timeline */}
        <div className="glass-panel" style={{ padding: "24px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
            <div>
              <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>Event Sequence Timeline</h3>
              <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)" }}>
                Human-readable chronological activity sequence
              </p>
            </div>
            <span className="badge badge-gray">{events.length} Events</span>
          </div>

          <div style={{ maxHeight: "380px", overflowY: "auto", paddingRight: "4px" }}>
            <SessionTimeline events={events} />
          </div>
        </div>
      </div>


      {/* Optional "View Raw Data" Toggle for Debugging (Section 10) */}
      <div className="glass-panel" style={{ padding: "20px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <FileCode size={18} color="var(--text-secondary)" />
            <div>
              <h4 style={{ fontSize: "0.9rem", fontWeight: 600 }}>Raw Telemetry Inspection</h4>
              <p style={{ fontSize: "0.75rem", color: "var(--text-tertiary)" }}>
                Inspect raw decrypted session JSON for technical debugging
              </p>
            </div>
          </div>

          <div style={{ display: "flex", gap: "8px" }}>
            {showRawJson && (
              <button onClick={handleCopyJson} className="apple-btn apple-btn-secondary" style={{ fontSize: "0.75rem" }}>
                {copied ? <Check size={12} color="var(--apple-green)" /> : <Copy size={12} />}
                <span>{copied ? "Copied" : "Copy"}</span>
              </button>
            )}
            <button
              onClick={() => setShowRawJson((prev) => !prev)}
              className="apple-btn apple-btn-secondary"
              style={{ fontSize: "0.78rem" }}
            >
              <span>{showRawJson ? "Hide Raw Data" : "View Raw Data"}</span>
              {showRawJson ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>
          </div>
        </div>

        {showRawJson && (
          <pre
            style={{
              marginTop: "16px",
              padding: "16px",
              borderRadius: "var(--radius-md)",
              backgroundColor: "var(--system-grouped-bg)",
              fontSize: "0.75rem",
              lineHeight: 1.45,
              maxHeight: "350px",
              overflowX: "auto",
              border: "1px solid var(--border-subtle)",
              fontFamily: "monospace",
            }}
          >
            {JSON.stringify(session, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
};
