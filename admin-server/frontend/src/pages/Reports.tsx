import React, { useState, useEffect } from "react";
import { Sparkles, Search, FileText, Bot, Loader2, X } from "lucide-react";
import { reportApi } from "../services/reportApi";
import { agentApi } from "../services/agentApi";
import type { AgentResponse } from "../services/agentApi";
import type { AIReport } from "../types";

import { AIInsightCard } from "../components/ai/AIInsightCard";
import { ReportViewer } from "../components/reports/ReportViewer";
import { LoadingState } from "../components/common/LoadingState";
import { ErrorState } from "../components/common/ErrorState";
import { EmptyState } from "../components/common/EmptyState";

export const Reports: React.FC = () => {
  const [reports, setReports] = useState<AIReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [genEmployee, setGenEmployee] = useState("");
  const [genLoading, setGenLoading] = useState(false);
  const [genResult, setGenResult] = useState<AgentResponse | null>(null);
  const [showGenerator, setShowGenerator] = useState(false);

  const loadReports = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await reportApi.getReports();
      setReports(data);
    } catch (err: any) {
      setError(err.message || "Failed to load agentic reports.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReports();
  }, []);

  if (loading) return <LoadingState message="Aggregating LangGraph agentic telemetry reports..." />;
  if (error) return <ErrorState message={error} onRetry={loadReports} />;

  const filtered = reports.filter((r) => {
    return (
      r.employee_name.toLowerCase().includes(search.toLowerCase()) ||
      r.overall_assessment.toLowerCase().includes(search.toLowerCase()) ||
      r.session_id.toLowerCase().includes(search.toLowerCase())
    );
  });

  return (
    <div style={{ padding: "28px", display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Intro Header Banner */}
      <div
        className="glass-panel"
        style={{
          padding: "20px 24px",
          background: "linear-gradient(135deg, rgba(88, 86, 214, 0.08), rgba(0, 122, 255, 0.05))",
          border: "1px solid rgba(88, 86, 214, 0.2)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "14px",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Sparkles size={20} color="var(--apple-indigo)" />
            <h2 style={{ fontSize: "1.15rem", fontWeight: 700 }}>AI Agentic Reports & Insights</h2>
          </div>
          <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", marginTop: "4px", maxWidth: "680px" }}>
            Synthesized by WorkGuard LangGraph specialized agents. This interface strictly delineates{" "}
            <strong>Raw Observed Data</strong> from <strong>AI-Generated Interpretations</strong> with verifiable evidence.
          </p>
        </div>

        {/* Search */}
        <div style={{ position: "relative", width: "260px" }}>
          <Search
            size={14}
            style={{
              position: "absolute",
              left: "12px",
              top: "50%",
              transform: "translateY(-50%)",
              color: "var(--text-tertiary)",
            }}
          />
          <input
            type="text"
            placeholder="Search reports or sessions..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              width: "100%",
              padding: "7px 12px 7px 32px",
              borderRadius: "var(--radius-pill)",
              border: "1px solid var(--border-subtle)",
              backgroundColor: "var(--system-grouped-bg)",
              color: "var(--text-primary)",
              fontSize: "0.8rem",
              outline: "none",
            }}
          />
        </div>
      </div>

      {/* On-Demand Report Generator */}
      <div className="glass-panel" style={{ padding: "20px 24px" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: showGenerator ? "16px" : "0",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <FileText size={16} color="var(--apple-purple)" />
            <h3 style={{ fontSize: "0.95rem", fontWeight: 700 }}>Generate Executive Report</h3>
          </div>
          <button
            onClick={() => {
              setShowGenerator(!showGenerator);
              if (!showGenerator) setGenResult(null);
            }}
            className="apple-btn apple-btn-secondary"
            style={{ fontSize: "0.75rem", padding: "5px 12px" }}
          >
            {showGenerator ? <X size={12} /> : <Bot size={12} />}
            <span>{showGenerator ? "Close" : "New Report"}</span>
          </button>
        </div>

        {showGenerator && (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                if (!genEmployee.trim()) return;
                setGenLoading(true);
                setGenResult(null);
                try {
                  const res = await agentApi.queryReportingAgent({
                    query: `Generate an executive activity report for ${genEmployee.trim()}`,
                  });
                  setGenResult(res);
                } catch (err: any) {
                  setGenResult({
                    answer: `Report generation failed: ${err.message || "Agent unreachable."}`,
                  });
                } finally {
                  setGenLoading(false);
                }
              }}
              style={{ display: "flex", gap: "10px" }}
            >
              <input
                type="text"
                placeholder="Employee name (e.g. arif.arshad, jane.engineer)..."
                value={genEmployee}
                onChange={(e) => setGenEmployee(e.target.value)}
                disabled={genLoading}
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
                disabled={!genEmployee.trim() || genLoading}
                className="apple-btn apple-btn-primary"
                style={{
                  borderRadius: "var(--radius-pill)",
                  padding: "0 20px",
                  background: "var(--apple-purple)",
                  boxShadow: "0 2px 8px rgba(175, 82, 222, 0.3)",
                  opacity: !genEmployee.trim() || genLoading ? 0.6 : 1,
                }}
              >
                {genLoading ? (
                  <>
                    <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} />
                    <span>Analyzing Telemetry...</span>
                  </>
                ) : (
                  <>
                    <FileText size={14} />
                    <span>Generate</span>
                  </>
                )}
              </button>
            </form>

            {/* Quick Employee Selection Chips */}
            <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
              <span style={{ fontSize: "0.72rem", color: "var(--text-tertiary)", fontWeight: 600 }}>
                Quick Select:
              </span>
              {["omar.mughal", "arif.arshad", "jane.engineer"].map((emp) => (
                <button
                  key={emp}
                  type="button"
                  onClick={() => setGenEmployee(emp)}
                  style={{
                    border: "1px solid var(--border-subtle)",
                    backgroundColor: genEmployee === emp ? "rgba(175, 82, 222, 0.15)" : "var(--system-grouped-bg)",
                    color: genEmployee === emp ? "var(--apple-purple)" : "var(--text-secondary)",
                    padding: "3px 10px",
                    borderRadius: "var(--radius-pill)",
                    fontSize: "0.72rem",
                    cursor: "pointer",
                    fontWeight: genEmployee === emp ? 700 : 500,
                  }}
                >
                  {emp}
                </button>
              ))}
            </div>

            {genResult && (
              <ReportViewer report={genResult} onClose={() => setGenResult(null)} />
            )}
          </div>
        )}
      </div>

      {/* Reports List */}
      {filtered.length === 0 ? (
        <EmptyState
          title="No AI Reports Available"
          description="Awaiting LangGraph workflow processing for completed session packages."
        />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {filtered.map((report) => (
            <AIInsightCard key={report.report_id} report={report} />
          ))}
        </div>
      )}
    </div>
  );
};
