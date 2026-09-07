import React, { useState, useEffect } from "react";
import {
  Server,
  Cpu,
  Database,
  HardDrive,
  Brain,
  Activity,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Layers,
} from "lucide-react";
import { chatApi } from "../services/chatApi";
import type { ChatStatusResponse } from "../services/chatApi";
import { systemApi } from "../services/systemApi";
import type {
  ProcessingStatusResponse,
  VectorStatsResponse,
  LlmHealthResponse,
} from "../services/systemApi";
import { LoadingState } from "../components/common/LoadingState";
import { StatCard } from "../components/common/StatCard";

type LoadState = "loading" | "loaded" | "error";

export const SystemStatus: React.FC = () => {
  const [chatStatus, setChatStatus] = useState<ChatStatusResponse | null>(null);
  const [processing, setProcessing] = useState<ProcessingStatusResponse | null>(null);
  const [vectors, setVectors] = useState<VectorStatsResponse | null>(null);
  const [llm, setLlm] = useState<LlmHealthResponse | null>(null);
  const [state, setState] = useState<LoadState>("loading");
  const [refreshing, setRefreshing] = useState(false);

  const loadAll = async () => {
    setState("loading");
    try {
      const [cs, ps, vs, lh] = await Promise.allSettled([
        chatApi.getStatus(),
        systemApi.getProcessingStatus(),
        systemApi.getVectorStats(),
        systemApi.getLlmHealth(),
      ]);
      if (cs.status === "fulfilled") setChatStatus(cs.value);
      if (ps.status === "fulfilled") setProcessing(ps.value);
      if (vs.status === "fulfilled") setVectors(vs.value);
      if (lh.status === "fulfilled") setLlm(lh.value);
      setState("loaded");
    } catch {
      setState("error");
    }
  };

  const refresh = async () => {
    setRefreshing(true);
    await loadAll();
    setRefreshing(false);
  };

  useEffect(() => {
    loadAll();
  }, []);

  if (state === "loading" && !chatStatus) {
    return <LoadingState message="Connecting to system telemetry endpoints..." />;
  }

  const StatusDot: React.FC<{ ok: boolean }> = ({ ok }) => (
    <span
      style={{
        display: "inline-block",
        width: "8px",
        height: "8px",
        borderRadius: "50%",
        backgroundColor: ok ? "var(--apple-green)" : "var(--apple-red)",
        boxShadow: ok
          ? "0 0 6px rgba(52, 199, 89, 0.5)"
          : "0 0 6px rgba(255, 59, 48, 0.5)",
      }}
    />
  );

  const StatusIcon: React.FC<{ ok: boolean }> = ({ ok }) =>
    ok ? (
      <CheckCircle2 size={15} color="var(--apple-green)" />
    ) : (
      <XCircle size={15} color="var(--apple-red)" />
    );

  const overallOk = chatStatus?.status === "ready";
  const llmOk = llm?.status === "ok" || llm?.status === "warning";
  const dbOk = chatStatus?.database?.status === "connected";

  return (
    <div style={{ padding: "28px", display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div>
          <h1 style={{ fontSize: "1.4rem", fontWeight: 700 }}>System Status</h1>
          <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", marginTop: "2px" }}>
            Full-stack observability for the WorkGuard Agent System
          </p>
        </div>
        <button
          onClick={refresh}
          disabled={refreshing}
          className="apple-btn apple-btn-secondary"
          style={{ fontSize: "0.8rem", opacity: refreshing ? 0.6 : 1 }}
        >
          <RefreshCw size={13} style={{ animation: refreshing ? "spin 1s linear infinite" : "none" }} />
          <span>{refreshing ? "Refreshing..." : "Refresh All"}</span>
        </button>
      </div>

      {/* Overall System Status Banner */}
      <div
        className="glass-panel"
        style={{
          padding: "20px 24px",
          display: "flex",
          alignItems: "center",
          gap: "14px",
          background: overallOk
            ? "linear-gradient(135deg, rgba(52, 199, 89, 0.06), rgba(0, 122, 255, 0.04))"
            : "linear-gradient(135deg, rgba(255, 59, 48, 0.08), rgba(255, 149, 0, 0.04))",
          border: overallOk
            ? "1px solid rgba(52, 199, 89, 0.2)"
            : "1px solid rgba(255, 59, 48, 0.2)",
        }}
      >
        <div
          style={{
            width: "44px",
            height: "44px",
            borderRadius: "12px",
            backgroundColor: overallOk ? "var(--apple-green-subtle)" : "var(--apple-red-subtle)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {overallOk ? (
            <CheckCircle2 size={22} color="var(--apple-green)" />
          ) : (
            <AlertTriangle size={22} color="var(--apple-red)" />
          )}
        </div>
        <div>
          <div style={{ fontSize: "1.05rem", fontWeight: 700 }}>
            {overallOk ? "All Systems Operational" : "System Degraded"}
          </div>
          <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
            {chatStatus?.api_layer || "Admin Chat API"} • Supervisor:{" "}
            {chatStatus?.supervisor || "unknown"}
          </div>
        </div>
      </div>

      {/* KPI Row */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "14px",
        }}
      >
        <StatCard
          title="LLM Engine"
          value={llmOk ? "Online" : "Offline"}
          subtitle={llm?.configured_model || "—"}
          icon={Brain}
          iconColor={llmOk ? "var(--apple-green)" : "var(--apple-red)"}
          iconBg={llmOk ? "var(--apple-green-subtle)" : "var(--apple-red-subtle)"}
        />
        <StatCard
          title="PostgreSQL"
          value={dbOk ? "Connected" : "Error"}
          subtitle={`${chatStatus?.database?.total_sessions ?? 0} sessions`}
          icon={Database}
          iconColor={dbOk ? "var(--apple-green)" : "var(--apple-red)"}
          iconBg={dbOk ? "var(--apple-green-subtle)" : "var(--apple-red-subtle)"}
        />
        <StatCard
          title="FAISS Vectors"
          value={vectors?.faiss_total_vectors ?? "—"}
          subtitle={`${vectors?.indexed_sessions_count ?? 0} sessions indexed`}
          icon={HardDrive}
          iconColor="var(--apple-indigo)"
          iconBg="var(--apple-indigo-subtle)"
        />
        <StatCard
          title="Processed Jobs"
          value={processing?.stats?.completed ?? "—"}
          subtitle={`${processing?.stats?.pending ?? 0} pending`}
          icon={Layers}
          iconColor="var(--apple-teal)"
          iconBg="rgba(48, 176, 199, 0.12)"
        />
      </div>

      {/* Agent Roster + LLM Details */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
          gap: "20px",
        }}
      >
        {/* Agent Roster */}
        <div className="glass-panel" style={{ padding: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
            <Cpu size={16} color="var(--apple-blue)" />
            <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>Agent Workforce</h3>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {chatStatus?.agents &&
              Object.entries(chatStatus.agents).map(([name, status]) => {
                const ok = status === "ready";
                const label = name
                  .replace(/_/g, " ")
                  .replace(/\b\w/g, (c) => c.toUpperCase());
                return (
                  <div
                    key={name}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: "10px 14px",
                      borderRadius: "var(--radius-md)",
                      backgroundColor: "var(--system-grouped-bg)",
                      border: "1px solid var(--border-subtle)",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                      <StatusDot ok={ok} />
                      <span style={{ fontWeight: 600, fontSize: "0.85rem" }}>{label}</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <StatusIcon ok={ok} />
                      <span
                        style={{
                          fontSize: "0.75rem",
                          fontWeight: 600,
                          color: ok ? "var(--apple-green)" : "var(--apple-red)",
                          textTransform: "uppercase",
                        }}
                      >
                        {status}
                      </span>
                    </div>
                  </div>
                );
              })}
          </div>
        </div>

        {/* LLM & Model Details */}
        <div className="glass-panel" style={{ padding: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
            <Brain size={16} color="var(--apple-purple)" />
            <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>LLM Engine Details</h3>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "12px", fontSize: "0.85rem" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                padding: "10px 14px",
                borderRadius: "var(--radius-md)",
                backgroundColor: "var(--system-grouped-bg)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <span style={{ color: "var(--text-secondary)" }}>Status</span>
              <span style={{ fontWeight: 600, color: llmOk ? "var(--apple-green)" : "var(--apple-red)" }}>
                {llm?.status?.toUpperCase() || "UNKNOWN"}
              </span>
            </div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                padding: "10px 14px",
                borderRadius: "var(--radius-md)",
                backgroundColor: "var(--system-grouped-bg)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <span style={{ color: "var(--text-secondary)" }}>Base URL</span>
              <span style={{ fontWeight: 600, fontFamily: "monospace", fontSize: "0.8rem" }}>
                {llm?.base_url || "—"}
              </span>
            </div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                padding: "10px 14px",
                borderRadius: "var(--radius-md)",
                backgroundColor: "var(--system-grouped-bg)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <span style={{ color: "var(--text-secondary)" }}>Active Model</span>
              <span className="badge badge-indigo">{llm?.configured_model || "—"}</span>
            </div>
            <div
              style={{
                padding: "10px 14px",
                borderRadius: "var(--radius-md)",
                backgroundColor: "var(--system-grouped-bg)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <div style={{ color: "var(--text-secondary)", marginBottom: "6px" }}>Available Models</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                {llm?.available_models?.map((m) => (
                  <span
                    key={m}
                    className="badge badge-gray"
                    style={{ fontSize: "0.72rem" }}
                  >
                    {m}
                  </span>
                )) || <span style={{ color: "var(--text-tertiary)" }}>None detected</span>}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Processing Pipeline + Vector Store */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
          gap: "20px",
        }}
      >
        {/* Processing Pipeline Jobs */}
        <div className="glass-panel" style={{ padding: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
            <Activity size={16} color="var(--apple-teal)" />
            <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>Processing Pipeline</h3>
          </div>

          {/* Stats row */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4, 1fr)",
              gap: "8px",
              marginBottom: "16px",
            }}
          >
            {[
              { label: "Completed", value: processing?.stats?.completed ?? 0, color: "var(--apple-green)" },
              { label: "Pending", value: processing?.stats?.pending ?? 0, color: "var(--apple-orange)" },
              { label: "Processing", value: processing?.stats?.processing ?? 0, color: "var(--apple-blue)" },
              { label: "Failed", value: processing?.stats?.failed ?? 0, color: "var(--apple-red)" },
            ].map((s) => (
              <div
                key={s.label}
                style={{
                  textAlign: "center",
                  padding: "10px 6px",
                  borderRadius: "var(--radius-md)",
                  backgroundColor: "var(--system-grouped-bg)",
                  border: "1px solid var(--border-subtle)",
                }}
              >
                <div style={{ fontSize: "1.2rem", fontWeight: 700, color: s.color }}>{s.value}</div>
                <div style={{ fontSize: "0.68rem", color: "var(--text-tertiary)", fontWeight: 600 }}>
                  {s.label}
                </div>
              </div>
            ))}
          </div>

          {/* Recent jobs */}
          <div style={{ fontSize: "0.72rem", fontWeight: 700, color: "var(--text-tertiary)", marginBottom: "8px", textTransform: "uppercase" }}>
            Recent Jobs
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px", maxHeight: "200px", overflowY: "auto" }}>
            {processing?.recent_jobs?.map((job) => (
              <div
                key={job.session_id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "8px 12px",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: "var(--system-grouped-bg)",
                  border: "1px solid var(--border-separator)",
                  fontSize: "0.8rem",
                }}
              >
                <span style={{ fontFamily: "monospace", fontSize: "0.75rem" }}>
                  {job.session_id.slice(0, 20)}
                </span>
                <span
                  className={`badge ${
                    job.status === "completed"
                      ? "badge-green"
                      : job.status === "failed"
                        ? "badge-red"
                        : "badge-orange"
                  }`}
                  style={{ fontSize: "0.68rem" }}
                >
                  {job.status}
                </span>
              </div>
            ))}
            {(!processing?.recent_jobs || processing.recent_jobs.length === 0) && (
              <div style={{ color: "var(--text-tertiary)", fontSize: "0.8rem", textAlign: "center", padding: "12px" }}>
                No recent processing jobs
              </div>
            )}
          </div>
        </div>

        {/* Vector Store Details */}
        <div className="glass-panel" style={{ padding: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
            <Server size={16} color="var(--apple-indigo)" />
            <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>FAISS Vector Store</h3>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "12px", fontSize: "0.85rem" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                padding: "10px 14px",
                borderRadius: "var(--radius-md)",
                backgroundColor: "var(--system-grouped-bg)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <span style={{ color: "var(--text-secondary)" }}>Total Vectors</span>
              <span style={{ fontWeight: 700, fontSize: "1rem" }}>
                {vectors?.faiss_total_vectors ?? "—"}
              </span>
            </div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                padding: "10px 14px",
                borderRadius: "var(--radius-md)",
                backgroundColor: "var(--system-grouped-bg)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <span style={{ color: "var(--text-secondary)" }}>Dimension</span>
              <span style={{ fontWeight: 600 }}>{vectors?.faiss_dimension ?? "—"}</span>
            </div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                padding: "10px 14px",
                borderRadius: "var(--radius-md)",
                backgroundColor: "var(--system-grouped-bg)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <span style={{ color: "var(--text-secondary)" }}>Indexed Sessions</span>
              <span style={{ fontWeight: 600 }}>{vectors?.indexed_sessions_count ?? "—"}</span>
            </div>

            {/* Vectors by doc type */}
            {vectors?.vectors_by_doc_type && Object.keys(vectors.vectors_by_doc_type).length > 0 && (
              <div
                style={{
                  padding: "10px 14px",
                  borderRadius: "var(--radius-md)",
                  backgroundColor: "var(--system-grouped-bg)",
                  border: "1px solid var(--border-subtle)",
                }}
              >
                <div style={{ color: "var(--text-secondary)", marginBottom: "8px" }}>
                  Vectors by Document Type
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                  {Object.entries(vectors.vectors_by_doc_type).map(([docType, count]) => (
                    <div
                      key={docType}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <span style={{ fontSize: "0.8rem", fontFamily: "monospace" }}>
                        {docType}
                      </span>
                      <span className="badge badge-indigo" style={{ fontSize: "0.7rem" }}>
                        {count}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
