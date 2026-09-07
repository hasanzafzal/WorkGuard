import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  AlertOctagon,
  AlertTriangle,
  AlertCircle,
  Info,
  X,
  Sparkles,
  Bot,
  Loader2,
} from "lucide-react";
import { securityApi } from "../services/securityApi";
import { agentApi } from "../services/agentApi";
import type { AgentResponse } from "../services/agentApi";
import type { SecurityEvent } from "../types";

import { SeverityBadge } from "../components/common/SeverityBadge";
import { LoadingState } from "../components/common/LoadingState";
import { ErrorState } from "../components/common/ErrorState";
import { EmptyState } from "../components/common/EmptyState";
import { SourceReference } from "../components/ai/SourceReference";

export const Security: React.FC = () => {
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<SecurityEvent | null>(null);
  const [severityFilter, setSeverityFilter] = useState("all");
  const [aiInvestigation, setAiInvestigation] = useState<AgentResponse | null>(null);
  const [aiLoading, setAiLoading] = useState(false);

  const loadEvents = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await securityApi.getSecurityEvents();
      setEvents(data);
    } catch (err: any) {
      setError(err.message || "Failed to load security telemetry.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvents();
  }, []);

  if (loading) return <LoadingState message="Connecting to security agent audit feeds..." />;
  if (error) return <ErrorState message={error} onRetry={loadEvents} />;

  const criticalCount = events.filter((e) => e.severity === "CRITICAL").length;
  const highCount = events.filter((e) => e.severity === "HIGH").length;
  const mediumCount = events.filter((e) => e.severity === "MEDIUM").length;
  const lowCount = events.filter((e) => e.severity === "LOW").length;

  const filtered = events.filter((e) => {
    if (severityFilter === "all") return true;
    return e.severity.toLowerCase() === severityFilter.toLowerCase();
  });

  return (
    <div style={{ padding: "28px", display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* 1. Severity Breakdown Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "14px",
        }}
      >
        <div
          className="glass-panel"
          style={{
            padding: "16px",
            borderLeft: "4px solid #FF3B30",
            cursor: "pointer",
            backgroundColor: severityFilter === "critical" ? "var(--apple-red-subtle)" : undefined,
          }}
          onClick={() => setSeverityFilter(severityFilter === "critical" ? "all" : "critical")}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--apple-red)" }}>CRITICAL</span>
            <AlertOctagon size={16} color="var(--apple-red)" />
          </div>
          <div style={{ fontSize: "1.6rem", fontWeight: 700, marginTop: "6px" }}>{criticalCount}</div>
        </div>

        <div
          className="glass-panel"
          style={{
            padding: "16px",
            borderLeft: "4px solid #FF453A",
            cursor: "pointer",
            backgroundColor: severityFilter === "high" ? "var(--apple-red-subtle)" : undefined,
          }}
          onClick={() => setSeverityFilter(severityFilter === "high" ? "all" : "high")}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#FF453A" }}>HIGH ALERTS</span>
            <AlertTriangle size={16} color="#FF453A" />
          </div>
          <div style={{ fontSize: "1.6rem", fontWeight: 700, marginTop: "6px" }}>{highCount}</div>
        </div>

        <div
          className="glass-panel"
          style={{
            padding: "16px",
            borderLeft: "4px solid #FF9500",
            cursor: "pointer",
            backgroundColor: severityFilter === "medium" ? "var(--apple-orange-subtle)" : undefined,
          }}
          onClick={() => setSeverityFilter(severityFilter === "medium" ? "all" : "medium")}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#FF9500" }}>MEDIUM ALERTS</span>
            <AlertCircle size={16} color="#FF9500" />
          </div>
          <div style={{ fontSize: "1.6rem", fontWeight: 700, marginTop: "6px" }}>{mediumCount}</div>
        </div>

        <div
          className="glass-panel"
          style={{
            padding: "16px",
            borderLeft: "4px solid #007AFF",
            cursor: "pointer",
            backgroundColor: severityFilter === "low" ? "var(--apple-blue-subtle)" : undefined,
          }}
          onClick={() => setSeverityFilter(severityFilter === "low" ? "all" : "low")}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#007AFF" }}>LOW ALERTS</span>
            <Info size={16} color="#007AFF" />
          </div>
          <div style={{ fontSize: "1.6rem", fontWeight: 700, marginTop: "6px" }}>{lowCount}</div>
        </div>
      </div>

      {/* 2. Security Events Table */}
      <div className="glass-panel" style={{ padding: 0, overflow: "hidden" }}>
        <div
          style={{
            padding: "16px 20px",
            borderBottom: "1px solid var(--border-subtle)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>Security Events Log</h3>
            <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)" }}>
              Detections originating from security agents and integrity validations
            </p>
          </div>
          {severityFilter !== "all" && (
            <button
              onClick={() => setSeverityFilter("all")}
              className="badge badge-gray"
              style={{ border: "none", cursor: "pointer" }}
            >
              Clear Filter: {severityFilter.toUpperCase()} (Show All)
            </button>
          )}
        </div>

        {filtered.length === 0 ? (
          <EmptyState
            title="No Security Events"
            description="All monitored endpoints and session packages meet integrity standards."
          />
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border-subtle)", backgroundColor: "var(--system-grouped-bg)", textAlign: "left" }}>
                  <th style={{ padding: "12px 16px", color: "var(--text-tertiary)", fontWeight: 600 }}>SEVERITY</th>
                  <th style={{ padding: "12px 16px", color: "var(--text-tertiary)", fontWeight: 600 }}>EMPLOYEE</th>
                  <th style={{ padding: "12px 16px", color: "var(--text-tertiary)", fontWeight: 600 }}>DETECTION EVENT</th>
                  <th style={{ padding: "12px 16px", color: "var(--text-tertiary)", fontWeight: 600 }}>TIME</th>
                  <th style={{ padding: "12px 16px", color: "var(--text-tertiary)", fontWeight: 600, textAlign: "right" }}>INVESTIGATE</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((evt) => (
                  <tr
                    key={evt.event_id}
                    style={{
                      borderBottom: "1px solid var(--border-separator)",
                      transition: "background var(--transition-fast)",
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "var(--apple-blue-subtle)")}
                    onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
                  >
                    <td style={{ padding: "12px 16px" }}>
                      <SeverityBadge severity={evt.severity} />
                    </td>
                    <td style={{ padding: "12px 16px", fontWeight: 600 }}>
                      <Link to={`/employees/${evt.employee_id}`} style={{ color: "var(--text-primary)", textDecoration: "none" }}>
                        {evt.employee_name}
                      </Link>
                    </td>
                    <td style={{ padding: "12px 16px" }}>
                      <div style={{ fontWeight: 600 }}>{evt.detection_type}</div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "2px" }}>
                        {evt.evidence.slice(0, 75)}...
                      </div>
                    </td>
                    <td style={{ padding: "12px 16px", color: "var(--text-secondary)", fontSize: "0.8rem" }}>
                      {new Date(evt.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </td>
                    <td style={{ padding: "12px 16px", textAlign: "right" }}>
                      <button
                        onClick={() => setSelectedEvent(evt)}
                        className="apple-btn apple-btn-secondary"
                        style={{ padding: "5px 12px", fontSize: "0.75rem" }}
                      >
                        Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 3. Event Details Slide-Over / Modal View */}
      {selectedEvent && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(0, 0, 0, 0.4)",
            backdropFilter: "blur(8px)",
            WebkitBackdropFilter: "blur(8px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 50,
            padding: "20px",
          }}
          onClick={() => setSelectedEvent(null)}
        >
          <div
            className="glass-panel"
            style={{
              width: "100%",
              maxWidth: "600px",
              backgroundColor: "var(--system-surface-solid)",
              borderRadius: "var(--radius-xl)",
              boxShadow: "var(--shadow-modal)",
              overflow: "hidden",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div
              style={{
                padding: "16px 20px",
                borderBottom: "1px solid var(--border-subtle)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                backgroundColor: "var(--system-grouped-bg)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <SeverityBadge severity={selectedEvent.severity} />
                <span style={{ fontWeight: 700, fontSize: "0.95rem" }}>
                  {selectedEvent.detection_type}
                </span>
              </div>
              <button
                onClick={() => setSelectedEvent(null)}
                className="apple-btn apple-btn-subtle"
                style={{ padding: "4px 8px" }}
              >
                <X size={16} />
              </button>
            </div>

            {/* Details Content */}
            <div style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "16px" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", fontSize: "0.82rem" }}>
                <div>
                  <span style={{ color: "var(--text-tertiary)" }}>EMPLOYEE:</span>
                  <div style={{ fontWeight: 600, marginTop: "2px" }}>{selectedEvent.employee_name}</div>
                </div>
                <div>
                  <span style={{ color: "var(--text-tertiary)" }}>TIMESTAMP:</span>
                  <div style={{ fontWeight: 600, marginTop: "2px" }}>
                    {new Date(selectedEvent.timestamp).toLocaleString()}
                  </div>
                </div>
              </div>

              {/* Evidence */}
              <div>
                <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase" }}>
                  EVIDENCE / TELEMETRY SIGNAL
                </span>
                <div
                  style={{
                    padding: "12px",
                    borderRadius: "var(--radius-md)",
                    backgroundColor: "var(--system-grouped-bg)",
                    border: "1px solid var(--border-subtle)",
                    fontSize: "0.82rem",
                    lineHeight: 1.45,
                    marginTop: "6px",
                    fontFamily: "monospace",
                  }}
                >
                  {selectedEvent.evidence}
                </div>
              </div>

              {/* Related Session */}
              <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "0.82rem" }}>
                <span style={{ color: "var(--text-tertiary)" }}>RELATED SESSION:</span>
                <SourceReference sessionId={selectedEvent.related_session_id} />
              </div>

              {/* AI Analysis */}
              {selectedEvent.ai_analysis && (
                <div
                  style={{
                    padding: "12px 14px",
                    borderRadius: "var(--radius-md)",
                    backgroundColor: "rgba(88, 86, 214, 0.08)",
                    border: "1px solid rgba(88, 86, 214, 0.2)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
                    <Sparkles size={14} color="var(--apple-indigo)" />
                    <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--apple-indigo)" }}>
                      AI SECURITY AGENT ANALYSIS
                    </span>
                  </div>
                  <p style={{ fontSize: "0.82rem", color: "var(--text-primary)", lineHeight: 1.4 }}>
                    {selectedEvent.ai_analysis}
                  </p>
                </div>
              )}

              {/* Recommended Action */}
              {selectedEvent.recommended_action && (
                <div
                  style={{
                    padding: "12px 14px",
                    borderRadius: "var(--radius-md)",
                    backgroundColor: "var(--apple-blue-subtle)",
                    border: "1px solid rgba(0, 122, 255, 0.2)",
                  }}
                >
                  <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--apple-blue)" }}>
                    RECOMMENDED ADMINISTRATIVE ACTION
                  </span>
                  <p style={{ fontSize: "0.82rem", color: "var(--text-primary)", marginTop: "3px" }}>
                    {selectedEvent.recommended_action}
                  </p>
                </div>
              )}

              {/* AI Investigation Button */}
              <div
                style={{
                  padding: "14px",
                  borderRadius: "var(--radius-md)",
                  backgroundColor: "rgba(88, 86, 214, 0.06)",
                  border: "1px solid rgba(88, 86, 214, 0.15)",
                }}
              >
                <button
                  onClick={async () => {
                    setAiLoading(true);
                    setAiInvestigation(null);
                    try {
                      const res = await agentApi.querySecurityAgent({
                        query: `Investigate security event for employee ${selectedEvent.employee_name}: ${selectedEvent.evidence}`,
                        employee_id: selectedEvent.employee_id,
                      });
                      setAiInvestigation(res);
                    } catch (err: any) {
                      setAiInvestigation({
                        answer: `Investigation failed: ${err.message || "Agent unreachable."}`,
                      });
                    } finally {
                      setAiLoading(false);
                    }
                  }}
                  disabled={aiLoading}
                  className="apple-btn apple-btn-primary"
                  style={{
                    width: "100%",
                    justifyContent: "center",
                    fontSize: "0.82rem",
                    opacity: aiLoading ? 0.7 : 1,
                    marginBottom: aiInvestigation ? "12px" : "0",
                  }}
                >
                  {aiLoading ? (
                    <>
                      <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} />
                      <span>Investigating with Security Agent...</span>
                    </>
                  ) : (
                    <>
                      <Bot size={14} />
                      <span>Investigate with AI Agent</span>
                    </>
                  )}
                </button>

                {aiInvestigation && (
                  <div
                    style={{
                      padding: "12px 14px",
                      borderRadius: "var(--radius-md)",
                      backgroundColor: "rgba(88, 86, 214, 0.08)",
                      border: "1px solid rgba(88, 86, 214, 0.2)",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "6px" }}>
                      <Bot size={14} color="var(--apple-indigo)" />
                      <span style={{ fontSize: "0.72rem", fontWeight: 700, color: "var(--apple-indigo)", textTransform: "uppercase" }}>
                        Live Agent Forensic Analysis
                      </span>
                      {aiInvestigation.risk_level && (
                        <span
                          className={`badge ${
                            aiInvestigation.risk_level === "HIGH" || aiInvestigation.risk_level === "CRITICAL"
                              ? "badge-red"
                              : aiInvestigation.risk_level === "MEDIUM"
                                ? "badge-orange"
                                : "badge-green"
                          }`}
                          style={{ fontSize: "0.68rem" }}
                        >
                          Risk: {aiInvestigation.risk_level} ({aiInvestigation.risk_score ?? "?"})
                        </span>
                      )}
                    </div>
                    <p style={{ fontSize: "0.82rem", color: "var(--text-primary)", lineHeight: 1.5, whiteSpace: "pre-wrap" }}>
                      {aiInvestigation.answer}
                    </p>
                    {aiInvestigation.sources && aiInvestigation.sources.length > 0 && (
                      <div style={{ marginTop: "8px", display: "flex", flexWrap: "wrap", gap: "4px" }}>
                        {aiInvestigation.sources.map((s) => (
                          <span key={s} className="badge badge-gray" style={{ fontSize: "0.68rem" }}>
                            {s}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "8px" }}>
                <button
                  onClick={() => {
                    setSelectedEvent(null);
                    setAiInvestigation(null);
                  }}
                  className="apple-btn apple-btn-secondary"
                  style={{ fontSize: "0.8rem" }}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
