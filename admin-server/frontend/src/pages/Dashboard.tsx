import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Users,
  UserCheck,
  Layers,
  Clock,
  ShieldAlert,
  ArrowRight,
  Sparkles,
  Send,
  CheckCircle2,
  XCircle,
  Brain,
} from "lucide-react";
import { dashboardApi } from "../services/dashboardApi";
import { chatApi } from "../services/chatApi";
import type { ChatStatusResponse } from "../services/chatApi";
import type { DashboardData } from "../types";

import { StatCard } from "../components/common/StatCard";
import { StatusBadge } from "../components/common/StatusBadge";
import { SeverityBadge } from "../components/common/SeverityBadge";
import { ApplicationUsageChart } from "../components/charts/ApplicationUsageChart";
import { LoadingState } from "../components/common/LoadingState";
import { ErrorState } from "../components/common/ErrorState";

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [agentStatus, setAgentStatus] = useState<ChatStatusResponse | null>(null);
  const [quickChatInput, setQuickChatInput] = useState("");

  const loadDashboard = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await dashboardApi.getDashboard();
      setData(res);
    } catch (err: any) {
      setError(err.message || "Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
    chatApi.getStatus().then(setAgentStatus).catch(() => {});
  }, []);

  const handleQuickChat = (query?: string) => {
    const q = (query || quickChatInput).trim();
    if (!q) return;
    // Navigate to Chat page with the query pre-filled via state
    navigate("/chat", { state: { initialQuery: q } });
  };

  if (loading) return <LoadingState message="Loading workforce analytics & system telemetry..." />;
  if (error || !data) return <ErrorState message={error || "Failed to load dashboard."} onRetry={loadDashboard} />;

  const formatHours = (seconds: number) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${hrs}h ${mins}m`;
  };

  return (
    <div style={{ padding: "28px", display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* 0. Agent System Health Banner */}
      {agentStatus && (
        <div
          className="glass-panel"
          style={{
            padding: "16px 20px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            background:
              agentStatus.status === "ready"
                ? "linear-gradient(135deg, rgba(52, 199, 89, 0.06), rgba(0, 122, 255, 0.04))"
                : "linear-gradient(135deg, rgba(255, 149, 0, 0.08), rgba(255, 59, 48, 0.04))",
            border:
              agentStatus.status === "ready"
                ? "1px solid rgba(52, 199, 89, 0.2)"
                : "1px solid rgba(255, 149, 0, 0.25)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "10px",
                backgroundColor:
                  agentStatus.status === "ready"
                    ? "var(--apple-green-subtle)"
                    : "var(--apple-orange-subtle)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              {agentStatus.status === "ready" ? (
                <CheckCircle2 size={18} color="var(--apple-green)" />
              ) : (
                <XCircle size={18} color="var(--apple-orange)" />
              )}
            </div>
            <div>
              <div style={{ fontSize: "0.88rem", fontWeight: 700 }}>
                Agent System: {agentStatus.status === "ready" ? "All Operational" : "Degraded"}
              </div>
              <div style={{ fontSize: "0.72rem", color: "var(--text-secondary)", display: "flex", gap: "12px", marginTop: "2px" }}>
                {agentStatus.agents &&
                  Object.entries(agentStatus.agents).map(([name, status]) => (
                    <span key={name} style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                      <span
                        style={{
                          width: "6px",
                          height: "6px",
                          borderRadius: "50%",
                          backgroundColor: status === "ready" ? "var(--apple-green)" : "var(--apple-red)",
                          display: "inline-block",
                        }}
                      />
                      {name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()).replace(" Agent", "")}
                    </span>
                  ))}
              </div>
            </div>
          </div>
          <Link
            to="/system"
            className="apple-btn apple-btn-secondary"
            style={{ fontSize: "0.75rem", padding: "5px 12px" }}
          >
            <span>System Status</span>
            <ArrowRight size={12} />
          </Link>
        </div>
      )}

      {/* 1. Required KPI Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "16px",
        }}
      >
        <StatCard
          title="Total Employees"
          value={data.kpis.total_employees}
          subtitle="Monitored LAN endpoints"
          icon={Users}
          iconColor="var(--apple-blue)"
          iconBg="var(--apple-blue-subtle)"
        />
        <StatCard
          title="Active Employees"
          value={data.kpis.active_employees}
          subtitle="Currently active in session"
          icon={UserCheck}
          iconColor="var(--apple-green)"
          iconBg="var(--apple-green-subtle)"
          badgeText="Active"
          badgeColor="green"
        />
        <StatCard
          title="Total Sessions"
          value={data.kpis.total_sessions}
          subtitle="Recorded work packages"
          icon={Layers}
          iconColor="var(--apple-indigo)"
          iconBg="var(--apple-indigo-subtle)"
        />
        <StatCard
          title="Total Activity Time"
          value={formatHours(data.kpis.total_active_time_seconds)}
          subtitle="Aggregated workstation time"
          icon={Clock}
          iconColor="var(--apple-teal)"
          iconBg="rgba(48, 176, 199, 0.12)"
        />
        <StatCard
          title="Security Alerts"
          value={data.kpis.security_alerts}
          subtitle={data.kpis.security_alerts > 0 ? "Requires review" : "All clean"}
          icon={ShieldAlert}
          iconColor={data.kpis.security_alerts > 0 ? "var(--apple-red)" : "var(--apple-green)"}
          iconBg={data.kpis.security_alerts > 0 ? "var(--apple-red-subtle)" : "var(--apple-green-subtle)"}
          badgeText={data.kpis.security_alerts > 0 ? "Flagged" : "Normal"}
          badgeColor={data.kpis.security_alerts > 0 ? "red" : "green"}
        />
      </div>

      {/* 2. AI Overview / Insights Banner */}
      {data.ai_overview && (
        <div
          className="glass-panel"
          style={{
            padding: "20px 24px",
            background: "linear-gradient(135deg, rgba(88, 86, 214, 0.08), rgba(0, 122, 255, 0.05))",
            border: "1px solid rgba(88, 86, 214, 0.2)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "10px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Sparkles size={18} color="var(--apple-indigo)" />
              <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>AI Workforce Overview</h3>
              <span className="badge badge-indigo" style={{ fontSize: "0.68rem" }}>
                Confidence: {data.ai_overview.confidence}%
              </span>
            </div>
            <Link to="/reports" className="apple-btn apple-btn-secondary" style={{ fontSize: "0.78rem" }}>
              <span>View All Reports</span>
              <ArrowRight size={13} />
            </Link>
          </div>
          <p style={{ fontSize: "0.88rem", color: "var(--text-primary)", lineHeight: 1.5 }}>
            {data.ai_overview.summary}
          </p>
        </div>
      )}

      {/* 3. Middle Section: Workforce Overview & Application Usage Chart */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
          gap: "20px",
        }}
      >
        {/* A. Workforce Overview Table */}
        <div className="glass-panel" style={{ padding: "24px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
            <div>
              <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>Workforce Overview</h3>
              <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)" }}>
                Active staff endpoints and logged duration
              </p>
            </div>
            <Link to="/employees" className="apple-btn apple-btn-secondary" style={{ fontSize: "0.78rem" }}>
              <span>All Employees</span>
              <ArrowRight size={13} />
            </Link>
          </div>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border-subtle)", textAlign: "left" }}>
                  <th style={{ padding: "8px 10px", color: "var(--text-tertiary)" }}>EMPLOYEE</th>
                  <th style={{ padding: "8px 10px", color: "var(--text-tertiary)" }}>SESSIONS</th>
                  <th style={{ padding: "8px 10px", color: "var(--text-tertiary)" }}>ACTIVE TIME</th>
                  <th style={{ padding: "8px 10px", color: "var(--text-tertiary)" }}>STATUS</th>
                </tr>
              </thead>
              <tbody>
                {data.workforce.map((emp) => (
                  <tr key={emp.employee_id} style={{ borderBottom: "1px solid var(--border-separator)" }}>
                    <td style={{ padding: "10px 10px" }}>
                      <Link
                        to={`/employees/${emp.employee_id}`}
                        style={{ textDecoration: "none", color: "var(--apple-blue)", fontWeight: 600 }}
                      >
                        {emp.employee_name}
                      </Link>
                    </td>
                    <td style={{ padding: "10px 10px" }}>{emp.sessions_count}</td>
                    <td style={{ padding: "10px 10px" }}>{formatHours(emp.total_active_time_seconds)}</td>
                    <td style={{ padding: "10px 10px" }}>
                      <StatusBadge status={emp.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* B. Application Usage Chart */}
        <ApplicationUsageChart
          data={data.application_usage}
          title="Workforce Application Usage"
        />
      </div>

      {/* 4. Bottom Section: Recent Sessions & Security Alerts */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
          gap: "20px",
        }}
      >
        {/* C. Recent Sessions */}
        <div className="glass-panel" style={{ padding: "24px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
            <div>
              <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>Recent Sessions</h3>
              <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)" }}>
                Latest recorded employee work sessions
              </p>
            </div>
            <Link to="/sessions" className="apple-btn apple-btn-secondary" style={{ fontSize: "0.78rem" }}>
              <span>View Sessions</span>
              <ArrowRight size={13} />
            </Link>
          </div>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border-subtle)", textAlign: "left" }}>
                  <th style={{ padding: "8px 10px", color: "var(--text-tertiary)" }}>SESSION ID</th>
                  <th style={{ padding: "8px 10px", color: "var(--text-tertiary)" }}>EMPLOYEE</th>
                  <th style={{ padding: "8px 10px", color: "var(--text-tertiary)" }}>DURATION</th>
                  <th style={{ padding: "8px 10px", color: "var(--text-tertiary)" }}>EVENTS</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_sessions.slice(0, 5).map((s) => (
                  <tr key={s.session_id} style={{ borderBottom: "1px solid var(--border-separator)" }}>
                    <td style={{ padding: "10px 10px", fontFamily: "monospace" }}>
                      <Link to={`/sessions/${s.session_id}`} style={{ color: "var(--apple-blue)" }}>
                        {s.session_id}
                      </Link>
                    </td>
                    <td style={{ padding: "10px 10px", fontWeight: 500 }}>{s.employee_name}</td>
                    <td style={{ padding: "10px 10px" }}>{Math.round(s.duration_seconds / 60)}m</td>
                    <td style={{ padding: "10px 10px" }}>
                      <span className="badge badge-gray">{s.events_count}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* D. Security Alerts */}
        <div className="glass-panel" style={{ padding: "24px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
            <div>
              <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>Security Alerts</h3>
              <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)" }}>
                Active anomaly detections from security agents
              </p>
            </div>
            <Link to="/security" className="apple-btn apple-btn-secondary" style={{ fontSize: "0.78rem" }}>
              <span>Security Center</span>
              <ArrowRight size={13} />
            </Link>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {data.security_alerts.slice(0, 3).map((alert) => (
              <div
                key={alert.event_id}
                style={{
                  padding: "12px 14px",
                  borderRadius: "var(--radius-md)",
                  backgroundColor: "var(--system-grouped-bg)",
                  border: "1px solid var(--border-subtle)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                  <SeverityBadge severity={alert.severity} />
                  <span style={{ fontSize: "0.72rem", color: "var(--text-tertiary)" }}>
                    {new Date(alert.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </span>
                </div>
                <div style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--text-primary)" }}>
                  {alert.detection_type} — {alert.employee_name}
                </div>
                <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "2px", lineHeight: 1.35 }}>
                  {alert.evidence}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
      {/* 5. Quick Chat Bar */}
      <div
        className="glass-panel"
        style={{
          padding: "14px 20px",
          display: "flex",
          alignItems: "center",
          gap: "12px",
        }}
      >
        <div
          style={{
            width: "32px",
            height: "32px",
            borderRadius: "10px",
            backgroundColor: "var(--apple-blue-subtle)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "var(--apple-blue)",
            flexShrink: 0,
          }}
        >
          <Brain size={16} />
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleQuickChat();
          }}
          style={{ flex: 1, display: "flex", gap: "10px" }}
        >
          <input
            type="text"
            placeholder="Ask WorkGuard Copilot — e.g. 'Was arif's activity suspicious?'"
            value={quickChatInput}
            onChange={(e) => setQuickChatInput(e.target.value)}
            style={{
              flex: 1,
              padding: "10px 16px",
              borderRadius: "var(--radius-pill)",
              border: "1px solid var(--border-subtle)",
              backgroundColor: "var(--system-grouped-bg)",
              color: "var(--text-primary)",
              fontSize: "0.82rem",
              outline: "none",
            }}
          />
          <button
            type="submit"
            disabled={!quickChatInput.trim()}
            className="apple-btn apple-btn-primary"
            style={{
              borderRadius: "var(--radius-pill)",
              padding: "0 18px",
              opacity: !quickChatInput.trim() ? 0.5 : 1,
            }}
          >
            <Send size={14} />
            <span>Ask</span>
          </button>
        </form>
      </div>
    </div>
  );
};
