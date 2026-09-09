import React, { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import {
  User,
  ArrowLeft,
  Sparkles,
  ShieldCheck,
  Bot,
  ShieldAlert,
  Loader2,
} from "lucide-react";
import { employeeApi } from "../services/employeeApi";
import { agentApi } from "../services/agentApi";
import type { AgentResponse } from "../services/agentApi";
import type { EmployeeDetail } from "../types";

import { StatusBadge } from "../components/common/StatusBadge";
import { SeverityBadge } from "../components/common/SeverityBadge";
import { ApplicationUsageChart } from "../components/charts/ApplicationUsageChart";
import { LoadingState } from "../components/common/LoadingState";
import { ErrorState } from "../components/common/ErrorState";
import { SourceReference } from "../components/ai/SourceReference";

export const EmployeeDetails: React.FC = () => {
  const { employeeId } = useParams<{ employeeId: string }>();
  const [employee, setEmployee] = useState<EmployeeDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sessionAnalysis, setSessionAnalysis] = useState<AgentResponse | null>(null);
  const [securityAnalysis, setSecurityAnalysis] = useState<AgentResponse | null>(null);
  const [sessionAnalysisLoading, setSessionAnalysisLoading] = useState(false);
  const [securityAnalysisLoading, setSecurityAnalysisLoading] = useState(false);

  const loadEmployee = async () => {
    if (!employeeId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await employeeApi.getEmployeeById(employeeId);
      setEmployee(data);
    } catch (err: any) {
      setError(err.message || "Failed to load employee details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEmployee();
  }, [employeeId]);

  if (loading) return <LoadingState message="Retrieving employee telemetry..." />;
  if (error || !employee) return <ErrorState message={error || "Employee not found."} onRetry={loadEmployee} />;

  const formatHours = (seconds: number) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${hrs}h ${mins}m`;
  };

  return (
    <div style={{ padding: "28px", display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Back Link & Header */}
      <div>
        <Link
          to="/employees"
          className="apple-btn apple-btn-secondary"
          style={{ display: "inline-flex", fontSize: "0.78rem", marginBottom: "14px" }}
        >
          <ArrowLeft size={13} />
          <span>Back to Employees</span>
        </Link>

        <div className="glass-panel" style={{ padding: "24px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
              <div
                style={{
                  width: "52px",
                  height: "52px",
                  borderRadius: "16px",
                  backgroundColor: "var(--apple-blue)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#FFF",
                  boxShadow: "0 4px 14px rgba(0, 122, 255, 0.35)",
                }}
              >
                <User size={28} />
              </div>
              <div>
                <h1 style={{ fontSize: "1.4rem", fontWeight: 700 }}>
                  {employee.employee_name}
                </h1>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "4px" }}>
                  <span style={{ fontFamily: "monospace", fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                    {employee.employee_id}
                  </span>
                  <StatusBadge status={employee.status} />
                </div>
              </div>
            </div>

            {/* Quick stats badges */}
            <div style={{ display: "flex", gap: "12px" }}>
              <div style={{ padding: "10px 16px", borderRadius: "var(--radius-md)", backgroundColor: "var(--system-grouped-bg)", textAlign: "center" }}>
                <div style={{ fontSize: "0.7rem", color: "var(--text-tertiary)", fontWeight: 600 }}>TOTAL ACTIVE TIME</div>
                <div style={{ fontSize: "1.2rem", fontWeight: 700 }}>{formatHours(employee.total_active_time_seconds)}</div>
              </div>
              <div style={{ padding: "10px 16px", borderRadius: "var(--radius-md)", backgroundColor: "var(--system-grouped-bg)", textAlign: "center" }}>
                <div style={{ fontSize: "0.7rem", color: "var(--text-tertiary)", fontWeight: 600 }}>SESSIONS</div>
                <div style={{ fontSize: "1.2rem", fontWeight: 700 }}>{employee.sessions_count}</div>
              </div>
              <div style={{ padding: "10px 16px", borderRadius: "var(--radius-md)", backgroundColor: "var(--system-grouped-bg)", textAlign: "center" }}>
                <div style={{ fontSize: "0.7rem", color: "var(--text-tertiary)", fontWeight: 600 }}>SECURITY ALERTS</div>
                <div style={{ fontSize: "1.2rem", fontWeight: 700, color: employee.security_alert_count > 0 ? "var(--apple-red)" : "var(--apple-green)" }}>
                  {employee.security_alert_count}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* AI Observations & Confidence */}
      {employee.ai_observations && (
        <div
          className="glass-panel"
          style={{
            padding: "20px 24px",
            backgroundColor: "rgba(88, 86, 214, 0.05)",
            border: "1px solid rgba(88, 86, 214, 0.2)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Sparkles size={17} color="var(--apple-indigo)" />
              <h3 style={{ fontSize: "0.95rem", fontWeight: 700 }}>AI Behavioral Observations</h3>
            </div>
            {employee.ai_confidence && (
              <span className="badge badge-indigo" style={{ fontSize: "0.7rem" }}>
                AI Confidence: {employee.ai_confidence}%
              </span>
            )}
          </div>

          <ul style={{ paddingLeft: "18px", fontSize: "0.85rem", display: "flex", flexDirection: "column", gap: "5px" }}>
            {employee.ai_observations.map((obs, idx) => (
              <li key={idx}>{obs}</li>
            ))}
          </ul>

          {employee.evidence_sessions && (
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "12px", fontSize: "0.75rem" }}>
              <span style={{ color: "var(--text-tertiary)", fontWeight: 600 }}>SOURCE SESSIONS:</span>
              {employee.evidence_sessions.map((sid) => (
                <SourceReference key={sid} sessionId={sid} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* On-Demand Agent Analysis */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
          gap: "16px",
        }}
      >
        {/* Session Activity Analysis */}
        <div className="glass-panel" style={{ padding: "20px 24px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
            <Bot size={16} color="var(--apple-blue)" />
            <h3 style={{ fontSize: "0.95rem", fontWeight: 700 }}>AI Activity Analysis</h3>
          </div>
          <button
            onClick={async () => {
              setSessionAnalysisLoading(true);
              setSessionAnalysis(null);
              try {
                const res = await agentApi.querySessionAgent({
                  query: `Give me a comprehensive activity summary for employee ${employee.employee_name}`,
                  employee_id: employee.employee_id,
                });
                setSessionAnalysis(res);
              } catch (err: any) {
                setSessionAnalysis({ answer: `Analysis failed: ${err.message || "Agent unreachable."}` });
              } finally {
                setSessionAnalysisLoading(false);
              }
            }}
            disabled={sessionAnalysisLoading}
            className="apple-btn apple-btn-primary"
            style={{
              width: "100%",
              justifyContent: "center",
              fontSize: "0.82rem",
              opacity: sessionAnalysisLoading ? 0.7 : 1,
              marginBottom: sessionAnalysis ? "12px" : "0",
            }}
          >
            {sessionAnalysisLoading ? (
              <>
                <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} />
                <span>Analyzing with Session Agent...</span>
              </>
            ) : (
              <>
                <Bot size={14} />
                <span>Analyze Activity with AI</span>
              </>
            )}
          </button>
          {sessionAnalysis && (
            <div
              style={{
                padding: "12px",
                borderRadius: "var(--radius-md)",
                backgroundColor: "rgba(0, 122, 255, 0.06)",
                border: "1px solid rgba(0, 122, 255, 0.15)",
                fontSize: "0.82rem",
                lineHeight: 1.5,
                whiteSpace: "pre-wrap",
              }}
            >
              {sessionAnalysis.answer}
              {sessionAnalysis.sources && sessionAnalysis.sources.length > 0 && (
                <div style={{ marginTop: "8px", display: "flex", flexWrap: "wrap", gap: "4px" }}>
                  {sessionAnalysis.sources.map((s) => (
                    <span key={s} className="badge badge-gray" style={{ fontSize: "0.68rem" }}>{s}</span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Security Assessment */}
        <div className="glass-panel" style={{ padding: "20px 24px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
            <ShieldAlert size={16} color="var(--apple-orange)" />
            <h3 style={{ fontSize: "0.95rem", fontWeight: 700 }}>AI Security Assessment</h3>
          </div>
          <button
            onClick={async () => {
              setSecurityAnalysisLoading(true);
              setSecurityAnalysis(null);
              try {
                const res = await agentApi.querySecurityAgent({
                  query: `Was ${employee.employee_name}'s activity suspicious? Provide a security risk assessment.`,
                  employee_id: employee.employee_id,
                });
                setSecurityAnalysis(res);
              } catch (err: any) {
                setSecurityAnalysis({ answer: `Assessment failed: ${err.message || "Agent unreachable."}` });
              } finally {
                setSecurityAnalysisLoading(false);
              }
            }}
            disabled={securityAnalysisLoading}
            className="apple-btn apple-btn-primary"
            style={{
              width: "100%",
              justifyContent: "center",
              fontSize: "0.82rem",
              background: "var(--apple-orange)",
              boxShadow: "0 2px 8px rgba(255, 149, 0, 0.25)",
              opacity: securityAnalysisLoading ? 0.7 : 1,
              marginBottom: securityAnalysis ? "12px" : "0",
            }}
          >
            {securityAnalysisLoading ? (
              <>
                <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} />
                <span>Running Security Assessment...</span>
              </>
            ) : (
              <>
                <ShieldAlert size={14} />
                <span>Run Security Assessment</span>
              </>
            )}
          </button>
          {securityAnalysis && (
            <div
              style={{
                padding: "12px",
                borderRadius: "var(--radius-md)",
                backgroundColor: "rgba(255, 149, 0, 0.06)",
                border: "1px solid rgba(255, 149, 0, 0.15)",
                fontSize: "0.82rem",
                lineHeight: 1.5,
                whiteSpace: "pre-wrap",
              }}
            >
              {securityAnalysis.risk_level && (
                <div style={{ marginBottom: "8px" }}>
                  <span
                    className={`badge ${
                      securityAnalysis.risk_level === "HIGH" || securityAnalysis.risk_level === "CRITICAL"
                        ? "badge-red"
                        : securityAnalysis.risk_level === "MEDIUM"
                          ? "badge-orange"
                          : "badge-green"
                    }`}
                  >
                    Risk: {securityAnalysis.risk_level} ({securityAnalysis.risk_score ?? "?"})
                  </span>
                </div>
              )}
              {securityAnalysis.answer}
              {securityAnalysis.sources && securityAnalysis.sources.length > 0 && (
                <div style={{ marginTop: "8px", display: "flex", flexWrap: "wrap", gap: "4px" }}>
                  {securityAnalysis.sources.map((s) => (
                    <span key={s} className="badge badge-gray" style={{ fontSize: "0.68rem" }}>{s}</span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Application Usage Breakdown */}
      <ApplicationUsageChart
        data={employee.applications_used}
        title={`Application Usage Breakdown — ${employee.employee_name}`}
      />

      {/* Session History & Security Events */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
          gap: "20px",
        }}
      >
        {/* Session History */}
        <div className="glass-panel" style={{ padding: "24px" }}>
          <h3 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: "16px" }}>Session History</h3>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border-subtle)", textAlign: "left" }}>
                  <th style={{ padding: "8px 10px", color: "var(--text-tertiary)" }}>SESSION ID</th>
                  <th style={{ padding: "8px 10px", color: "var(--text-tertiary)" }}>DURATION</th>
                  <th style={{ padding: "8px 10px", color: "var(--text-tertiary)" }}>EVENTS</th>
                  <th style={{ padding: "8px 10px", color: "var(--text-tertiary)" }}>ACTION</th>
                </tr>
              </thead>
              <tbody>
                {employee.session_history.map((s) => (
                  <tr key={s.session_id} style={{ borderBottom: "1px solid var(--border-separator)" }}>
                    <td style={{ padding: "10px 10px", fontFamily: "monospace" }}>{s.session_id}</td>
                    <td style={{ padding: "10px 10px" }}>{Math.round(s.duration_seconds / 60)}m</td>
                    <td style={{ padding: "10px 10px" }}>{s.events_count}</td>
                    <td style={{ padding: "10px 10px" }}>
                      <Link to={`/sessions/${s.session_id}`} className="badge badge-blue" style={{ textDecoration: "none" }}>
                        Inspect
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Security Events Associated */}
        <div className="glass-panel" style={{ padding: "24px" }}>
          <h3 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: "16px" }}>Associated Security Events</h3>
          {employee.security_events.length === 0 ? (
            <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--apple-green)", fontSize: "0.85rem" }}>
              <ShieldCheck size={18} />
              <span>No security anomalies associated with this employee.</span>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {employee.security_events.map((sec) => (
                <div
                  key={sec.event_id}
                  style={{
                    padding: "12px",
                    borderRadius: "var(--radius-md)",
                    backgroundColor: "var(--system-grouped-bg)",
                    border: "1px solid var(--border-subtle)",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                    <SeverityBadge severity={sec.severity} />
                    <span style={{ fontSize: "0.72rem", color: "var(--text-tertiary)" }}>
                      {new Date(sec.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  <div style={{ fontWeight: 600, fontSize: "0.82rem" }}>{sec.detection_type}</div>
                  <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "2px" }}>
                    {sec.evidence}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
