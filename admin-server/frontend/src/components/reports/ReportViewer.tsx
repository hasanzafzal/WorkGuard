import React, { useState } from "react";
import {
  Download,
  Printer,
  Copy,
  Check,
  FileText,
  ShieldCheck,
  TrendingUp,
  Clock,
  Layers,
  Sparkles,
  Bot,
} from "lucide-react";
import type { AgentResponse } from "../../services/agentApi";

interface ReportViewerProps {
  report: AgentResponse;
  onClose?: () => void;
}

export const ReportViewer: React.FC<ReportViewerProps> = ({ report, onClose }) => {
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<"formatted" | "raw">("formatted");

  const metrics = report.metrics || {};
  const totalDurationMin = Math.round((metrics.total_duration_seconds || 0) / 60);
  const productiveMin = Math.round((metrics.productive_seconds || 0) / 60);
  const productivityPct = metrics.productivity_percentage || 0;
  const sessionsCount = metrics.sessions_count || (metrics.sessions ? metrics.sessions.length : 0);
  const apps: any[] = metrics.applications || [];
  const processes: string[] = metrics.processes_used || [];
  const sec = metrics.security || {};
  const riskLevel = sec.risk_level || report.risk_level || "LOW";
  const riskScore = sec.risk_score ?? report.risk_score ?? 0;

  const employeeName = report.employee_name || metrics.profile?.employee_name || "Employee";
  const employeeId = report.employee_id || metrics.profile?.employee_id || "Enterprise";

  // Actions
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(report.answer);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  const handleDownloadMarkdown = () => {
    const filename = `Executive_Report_${employeeName.replace(/[^a-zA-Z0-9_-]/g, "_")}_${new Date().toISOString().slice(0, 10)}.md`;
    const blob = new Blob([report.answer], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleDownloadJSON = () => {
    const filename = `Executive_Report_${employeeName.replace(/[^a-zA-Z0-9_-]/g, "_")}_${new Date().toISOString().slice(0, 10)}.json`;
    const data = {
      employee_id: employeeId,
      employee_name: employeeName,
      generated_at: new Date().toISOString(),
      report_text: report.answer,
      metrics: report.metrics,
      sources: report.sources,
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handlePrint = () => {
    window.print();
  };

  // Simple Markdown Parser to render tables, headings, and lists
  const renderMarkdown = (content: string) => {
    const lines = content.split("\n");
    const elements: React.ReactNode[] = [];
    let tableLines: string[] = [];
    let inTable = false;

    const flushTable = (key: string) => {
      if (tableLines.length >= 2) {
        const headerCells = tableLines[0]
          .split("|")
          .filter((_, idx, arr) => idx > 0 && idx < arr.length - 1)
          .map((c) => c.trim());
        const bodyRows = tableLines.slice(2).map((row) =>
          row
            .split("|")
            .filter((_, idx, arr) => idx > 0 && idx < arr.length - 1)
            .map((c) => c.trim())
        );

        elements.push(
          <div
            key={key}
            style={{
              overflowX: "auto",
              margin: "14px 0",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: "0.82rem",
                textAlign: "left",
              }}
            >
              <thead>
                <tr style={{ backgroundColor: "var(--system-grouped-bg)", borderBottom: "1px solid var(--border-subtle)" }}>
                  {headerCells.map((h, i) => (
                    <th key={i} style={{ padding: "8px 12px", fontWeight: 700, color: "var(--text-secondary)" }}>
                      {h.replace(/\*\*/g, "")}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {bodyRows.map((row, rIdx) => (
                  <tr
                    key={rIdx}
                    style={{
                      borderBottom: rIdx === bodyRows.length - 1 ? "none" : "1px solid var(--border-subtle)",
                      backgroundColor: rIdx % 2 === 1 ? "rgba(0, 0, 0, 0.02)" : "transparent",
                    }}
                  >
                    {row.map((cell, cIdx) => (
                      <td key={cIdx} style={{ padding: "8px 12px", color: "var(--text-primary)" }}>
                        {formatInline(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }
      tableLines = [];
      inTable = false;
    };

    lines.forEach((line, idx) => {
      const trimmed = line.trim();

      // Check if table row
      if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
        inTable = true;
        tableLines.push(trimmed);
        return;
      } else if (inTable) {
        flushTable(`table-${idx}`);
      }

      if (trimmed.startsWith("# ")) {
        elements.push(
          <h1 key={idx} style={{ fontSize: "1.25rem", fontWeight: 800, margin: "16px 0 8px", color: "var(--text-primary)" }}>
            {trimmed.slice(2)}
          </h1>
        );
      } else if (trimmed.startsWith("## ")) {
        elements.push(
          <h2
            key={idx}
            style={{
              fontSize: "1.05rem",
              fontWeight: 700,
              margin: "20px 0 8px",
              paddingBottom: "4px",
              borderBottom: "1px solid var(--border-subtle)",
              color: "var(--text-primary)",
            }}
          >
            {trimmed.slice(3)}
          </h2>
        );
      } else if (trimmed.startsWith("### ")) {
        elements.push(
          <h3 key={idx} style={{ fontSize: "0.92rem", fontWeight: 700, margin: "14px 0 6px", color: "var(--text-primary)" }}>
            {trimmed.slice(4)}
          </h3>
        );
      } else if (trimmed === "---") {
        elements.push(<hr key={idx} style={{ border: "none", borderTop: "1px solid var(--border-subtle)", margin: "16px 0" }} />);
      } else if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
        elements.push(
          <div key={idx} style={{ display: "flex", gap: "8px", margin: "4px 0 4px 12px", fontSize: "0.85rem", lineHeight: 1.5 }}>
            <span style={{ color: "var(--apple-purple)" }}>•</span>
            <div>{formatInline(trimmed.slice(2))}</div>
          </div>
        );
      } else if (/^\d+\.\s/.test(trimmed)) {
        const match = trimmed.match(/^(\d+)\.\s(.*)$/);
        elements.push(
          <div key={idx} style={{ display: "flex", gap: "8px", margin: "4px 0 4px 12px", fontSize: "0.85rem", lineHeight: 1.5 }}>
            <span style={{ fontWeight: 700, color: "var(--apple-purple)" }}>{match ? match[1] : ""}.</span>
            <div>{match ? formatInline(match[2]) : trimmed}</div>
          </div>
        );
      } else if (trimmed.length > 0) {
        elements.push(
          <p key={idx} style={{ margin: "6px 0", fontSize: "0.86rem", lineHeight: 1.6, color: "var(--text-primary)" }}>
            {formatInline(trimmed)}
          </p>
        );
      }
    });

    if (inTable) {
      flushTable("table-end");
    }

    return elements;
  };

  // Simple inline parser for bold and code
  const formatInline = (text: string): React.ReactNode => {
    const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g);
    return parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={i}>{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith("`") && part.endsWith("`")) {
        return (
          <code
            key={i}
            style={{
              padding: "2px 5px",
              backgroundColor: "rgba(175, 82, 222, 0.08)",
              borderRadius: "4px",
              fontFamily: "monospace",
              fontSize: "0.8em",
              color: "var(--apple-purple)",
            }}
          >
            {part.slice(1, -1)}
          </code>
        );
      }
      return part;
    });
  };

  return (
    <div
      className="glass-panel printable-report"
      style={{
        padding: "24px",
        borderRadius: "var(--radius-lg)",
        backgroundColor: "var(--glass-bg)",
        border: "1px solid var(--border-subtle)",
        display: "flex",
        flexDirection: "column",
        gap: "20px",
        boxShadow: "0 8px 32px rgba(0, 0, 0, 0.08)",
      }}
    >
      {/* Header & Actions Toolbar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px",
          paddingBottom: "16px",
          borderBottom: "1px solid var(--border-subtle)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div
            style={{
              width: "36px",
              height: "36px",
              borderRadius: "10px",
              backgroundColor: "rgba(175, 82, 222, 0.12)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--apple-purple)",
            }}
          >
            <Bot size={20} />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <h3 style={{ fontSize: "1.05rem", fontWeight: 700 }}>Executive Activity Report</h3>
              <span className="badge badge-indigo" style={{ fontSize: "0.7rem" }}>
                {employeeName}
              </span>
              <span className="badge badge-green" style={{ fontSize: "0.7rem" }}>
                Verified Authoritative
              </span>
            </div>
            <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginTop: "2px" }}>
              Target ID: <code style={{ fontFamily: "monospace" }}>{employeeId}</code> • Generated:{" "}
              {new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="no-print" style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          <div
            style={{
              display: "flex",
              borderRadius: "var(--radius-pill)",
              backgroundColor: "var(--system-grouped-bg)",
              padding: "2px",
              border: "1px solid var(--border-subtle)",
              marginRight: "4px",
            }}
          >
            <button
              onClick={() => setActiveTab("formatted")}
              style={{
                border: "none",
                background: activeTab === "formatted" ? "var(--apple-purple)" : "transparent",
                color: activeTab === "formatted" ? "#fff" : "var(--text-secondary)",
                padding: "4px 12px",
                borderRadius: "var(--radius-pill)",
                fontSize: "0.72rem",
                fontWeight: 600,
                cursor: "pointer",
                transition: "all 0.2s ease",
              }}
            >
              Executive View
            </button>
            <button
              onClick={() => setActiveTab("raw")}
              style={{
                border: "none",
                background: activeTab === "raw" ? "var(--apple-purple)" : "transparent",
                color: activeTab === "raw" ? "#fff" : "var(--text-secondary)",
                padding: "4px 12px",
                borderRadius: "var(--radius-pill)",
                fontSize: "0.72rem",
                fontWeight: 600,
                cursor: "pointer",
                transition: "all 0.2s ease",
              }}
            >
              Raw Markdown
            </button>
          </div>

          <button
            onClick={handleCopy}
            className="apple-btn apple-btn-secondary"
            style={{ fontSize: "0.75rem", padding: "6px 12px" }}
            title="Copy Markdown report to clipboard"
          >
            {copied ? <Check size={13} color="var(--apple-green)" /> : <Copy size={13} />}
            <span>{copied ? "Copied!" : "Copy"}</span>
          </button>

          <button
            onClick={handleDownloadMarkdown}
            className="apple-btn apple-btn-secondary"
            style={{ fontSize: "0.75rem", padding: "6px 12px" }}
            title="Download full Markdown file"
          >
            <Download size={13} />
            <span>Markdown</span>
          </button>

          <button
            onClick={handleDownloadJSON}
            className="apple-btn apple-btn-secondary"
            style={{ fontSize: "0.75rem", padding: "6px 12px" }}
            title="Download structured JSON telemetry bundle"
          >
            <FileText size={13} />
            <span>JSON</span>
          </button>

          <button
            onClick={handlePrint}
            className="apple-btn apple-btn-primary"
            style={{
              fontSize: "0.75rem",
              padding: "6px 14px",
              background: "var(--apple-purple)",
            }}
            title="Print or export as PDF"
          >
            <Printer size={13} />
            <span>Print / PDF</span>
          </button>

          {onClose && (
            <button
              onClick={onClose}
              className="apple-btn apple-btn-secondary"
              style={{ fontSize: "0.75rem", padding: "6px 10px" }}
            >
              Close
            </button>
          )}
        </div>
      </div>

      {/* KPI Highlight Metric Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "14px",
        }}
      >
        <div
          style={{
            padding: "14px 16px",
            borderRadius: "var(--radius-md)",
            backgroundColor: "rgba(52, 199, 89, 0.06)",
            border: "1px solid rgba(52, 199, 89, 0.2)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
            <span style={{ fontSize: "0.72rem", fontWeight: 700, textTransform: "uppercase", color: "var(--apple-green)" }}>
              Productivity Index
            </span>
            <TrendingUp size={14} color="var(--apple-green)" />
          </div>
          <div style={{ fontSize: "1.45rem", fontWeight: 800, color: "var(--apple-green)" }}>
            {productivityPct}%
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "2px" }}>
            {productivityPct >= 60 ? "Optimal Focus" : "Standard Engagement"}
          </div>
        </div>

        <div
          style={{
            padding: "14px 16px",
            borderRadius: "var(--radius-md)",
            backgroundColor: "rgba(0, 122, 255, 0.06)",
            border: "1px solid rgba(0, 122, 255, 0.2)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
            <span style={{ fontSize: "0.72rem", fontWeight: 700, textTransform: "uppercase", color: "var(--apple-blue)" }}>
              Productive Active Time
            </span>
            <Clock size={14} color="var(--apple-blue)" />
          </div>
          <div style={{ fontSize: "1.45rem", fontWeight: 800, color: "var(--apple-blue)" }}>
            {productiveMin} <span style={{ fontSize: "0.9rem", fontWeight: 600 }}>min</span>
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "2px" }}>
            of {totalDurationMin} min monitored
          </div>
        </div>

        <div
          style={{
            padding: "14px 16px",
            borderRadius: "var(--radius-md)",
            backgroundColor: "rgba(175, 82, 222, 0.06)",
            border: "1px solid rgba(175, 82, 222, 0.2)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
            <span style={{ fontSize: "0.72rem", fontWeight: 700, textTransform: "uppercase", color: "var(--apple-purple)" }}>
              Monitored Sessions
            </span>
            <Layers size={14} color="var(--apple-purple)" />
          </div>
          <div style={{ fontSize: "1.45rem", fontWeight: 800, color: "var(--apple-purple)" }}>
            {sessionsCount}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "2px" }}>
            Authoritative session packages
          </div>
        </div>

        <div
          style={{
            padding: "14px 16px",
            borderRadius: "var(--radius-md)",
            backgroundColor: riskLevel === "HIGH" ? "rgba(255, 59, 48, 0.08)" : "rgba(88, 86, 214, 0.06)",
            border: riskLevel === "HIGH" ? "1px solid rgba(255, 59, 48, 0.2)" : "1px solid rgba(88, 86, 214, 0.2)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
            <span style={{ fontSize: "0.72rem", fontWeight: 700, textTransform: "uppercase", color: "var(--apple-indigo)" }}>
              Risk Level & Score
            </span>
            <ShieldCheck size={14} color="var(--apple-indigo)" />
          </div>
          <div style={{ fontSize: "1.45rem", fontWeight: 800, color: riskLevel === "HIGH" ? "var(--apple-red)" : "var(--apple-indigo)" }}>
            {riskLevel} <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>({riskScore}/100)</span>
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "2px" }}>
            {sec.total_findings || 0} anomalies detected
          </div>
        </div>
      </div>

      {/* Main Report Body */}
      {activeTab === "formatted" ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {/* Formatted Markdown Sections */}
          <div
            style={{
              padding: "20px 24px",
              borderRadius: "var(--radius-md)",
              backgroundColor: "var(--system-grouped-bg)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            {renderMarkdown(report.answer)}
          </div>

          {/* Interactive Application Focus Visualizer if apps present */}
          {apps.length > 0 && (
            <div
              style={{
                padding: "18px 22px",
                borderRadius: "var(--radius-md)",
                backgroundColor: "var(--system-grouped-bg)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "14px" }}>
                <Sparkles size={16} color="var(--apple-purple)" />
                <h4 style={{ fontSize: "0.92rem", fontWeight: 700 }}>Telemetry Focus Share Breakdown</h4>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {apps.map((a: any, idx: number) => {
                  const disp = a.display_name || a.process_name;
                  const pct = a.calculated_pct || Math.round((a.total_focus_seconds / Math.max(metrics.total_duration_seconds || 1, 1)) * 100);
                  const min = Math.round((a.total_focus_seconds || 0) / 60 * 10) / 10;
                  return (
                    <div key={idx} style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem" }}>
                        <span style={{ fontWeight: 600 }}>
                          {disp} <span style={{ color: "var(--text-tertiary)", fontWeight: 400 }}>({a.category || "general"})</span>
                        </span>
                        <span style={{ fontWeight: 700, color: "var(--apple-purple)" }}>
                          {min}m ({pct}%)
                        </span>
                      </div>
                      <div
                        style={{
                          width: "100%",
                          height: "6px",
                          borderRadius: "3px",
                          backgroundColor: "rgba(0, 0, 0, 0.06)",
                          overflow: "hidden",
                        }}
                      >
                        <div
                          style={{
                            width: `${Math.min(pct, 100)}%`,
                            height: "100%",
                            borderRadius: "3px",
                            backgroundColor: idx === 0 ? "var(--apple-purple)" : idx === 1 ? "var(--apple-blue)" : "var(--apple-indigo)",
                            transition: "width 0.4s ease",
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Executed Processes Pill Badges */}
          {processes.length > 0 && (
            <div
              style={{
                padding: "16px 20px",
                borderRadius: "var(--radius-md)",
                backgroundColor: "var(--system-grouped-bg)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <div style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "8px" }}>
                EXECUTED PROCESSES IN OBSERVED TELEMETRY ({processes.length}):
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                {processes.map((proc, pIdx) => (
                  <span
                    key={pIdx}
                    className="badge badge-gray"
                    style={{ fontFamily: "monospace", fontSize: "0.72rem", padding: "3px 8px" }}
                  >
                    {proc}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Raw Markdown View */
        <div
          style={{
            padding: "16px",
            borderRadius: "var(--radius-md)",
            backgroundColor: "var(--system-grouped-bg)",
            border: "1px solid var(--border-subtle)",
          }}
        >
          <pre
            style={{
              fontSize: "0.82rem",
              lineHeight: 1.5,
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              fontFamily: "monospace",
              color: "var(--text-primary)",
              margin: 0,
            }}
          >
            {report.answer}
          </pre>
        </div>
      )}

      {/* Cited Sources */}
      {report.sources && report.sources.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", alignItems: "center", fontSize: "0.75rem", paddingTop: "8px", borderTop: "1px solid var(--border-subtle)" }}>
          <span style={{ color: "var(--text-tertiary)", fontWeight: 600 }}>CITED SOURCES:</span>
          {report.sources.map((s, idx) => (
            <span key={idx} className="badge badge-gray" style={{ fontSize: "0.68rem" }}>
              {s}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};
