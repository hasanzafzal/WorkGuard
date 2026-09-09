import React, { useState } from "react";
import { Sparkles, Database, Download, Copy, Check } from "lucide-react";
import type { AIReport } from "../../types";
import { SourceReference } from "./SourceReference";


interface AIInsightCardProps {
  report: AIReport;
}

export const AIInsightCard: React.FC<AIInsightCardProps> = ({ report }) => {
  const [copied, setCopied] = useState(false);

  const handleDownload = () => {
    const md = `# AI Work Analysis: ${report.employee_name}\n**Date:** ${report.date} | **Confidence:** ${report.ai_confidence}%\n\n## Overall Assessment\n${report.overall_assessment}\n\n## Key Observations\n${report.key_observations.map((k) => `- ${k}`).join("\n")}\n\n## Raw Observed Telemetry\n- **Total Duration:** ${Math.round(report.raw_observed_data.total_duration_seconds / 60)} minutes\n- **Foreground Events:** ${report.raw_observed_data.event_count}\n- **Top Applications:** ${report.raw_observed_data.top_apps.join(", ")}\n\n## Evidence Sessions\n${(report.evidence_sessions || []).map((s) => `- ${s}`).join("\n")}\n`;
    const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `AI_Report_${report.employee_name.replace(/[^a-zA-Z0-9_-]/g, "_")}_${report.report_id}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleCopy = async () => {
    const text = `${report.employee_name} (${report.date}) - AI Analysis:\n${report.overall_assessment}\n\nObservations:\n${report.key_observations.map((k) => `• ${k}`).join("\n")}`;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div
      className="glass-panel"
      style={{
        padding: "24px",
        display: "flex",
        flexDirection: "column",
        gap: "20px",
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "10px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "1.1rem", fontWeight: 700 }}>
              AI Work Analysis
            </span>
            <span className="badge badge-indigo">
              <Sparkles size={11} />
              AI Agentic Workflow
            </span>
          </div>
          <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", marginTop: "3px" }}>
            Employee: <strong>{report.employee_name}</strong> • Date: {report.date}
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <button
            onClick={handleCopy}
            className="apple-btn apple-btn-secondary"
            style={{ fontSize: "0.72rem", padding: "5px 10px" }}
            title="Copy summary"
          >
            {copied ? <Check size={12} color="var(--apple-green)" /> : <Copy size={12} />}
            <span>{copied ? "Copied" : "Copy"}</span>
          </button>
          <button
            onClick={handleDownload}
            className="apple-btn apple-btn-secondary"
            style={{ fontSize: "0.72rem", padding: "5px 10px" }}
            title="Download report markdown"
          >
            <Download size={12} />
            <span>Download</span>
          </button>
          <div
            style={{
              textAlign: "right",
              padding: "6px 12px",
              borderRadius: "var(--radius-md)",
              backgroundColor: "var(--apple-blue-subtle)",
              border: "1px solid rgba(0, 122, 255, 0.2)",
            }}
          >
            <div style={{ fontSize: "0.64rem", color: "var(--text-tertiary)", fontWeight: 700, textTransform: "uppercase" }}>
              AI Confidence
            </div>
            <div style={{ fontSize: "1.15rem", fontWeight: 800, color: "var(--apple-blue)" }}>
              {report.ai_confidence}%
            </div>
          </div>
        </div>
      </div>

      {/* Distinction Section 1: AI-Generated Interpretation */}
      <div
        style={{
          padding: "16px 20px",
          borderRadius: "var(--radius-md)",
          backgroundColor: "rgba(88, 86, 214, 0.06)",
          border: "1px solid rgba(88, 86, 214, 0.2)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px" }}>
          <Sparkles size={14} color="var(--apple-indigo)" />
          <span style={{ fontSize: "0.72rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--apple-indigo)" }}>
            AI-GENERATED INTERPRETATION
          </span>
        </div>

        <p style={{ fontSize: "0.9rem", color: "var(--text-primary)", lineHeight: 1.5, marginBottom: "12px" }}>
          {report.overall_assessment}
        </p>

        <div style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "6px" }}>
          Key Observations:
        </div>
        <ul style={{ paddingLeft: "18px", fontSize: "0.82rem", display: "flex", flexDirection: "column", gap: "4px" }}>
          {report.key_observations.map((obs, idx) => (
            <li key={idx}>{obs}</li>
          ))}
        </ul>
      </div>

      {/* Distinction Section 2: Raw Observed Data */}
      <div
        style={{
          padding: "14px 18px",
          borderRadius: "var(--radius-md)",
          backgroundColor: "var(--system-grouped-bg)",
          border: "1px solid var(--border-subtle)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px" }}>
          <Database size={14} color="var(--text-secondary)" />
          <span style={{ fontSize: "0.72rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-secondary)" }}>
            RAW OBSERVED DATA (AUTHORITATIVE LAN TELEMETRY)
          </span>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: "10px",
            fontSize: "0.8rem",
          }}
        >
          <div>
            <span style={{ color: "var(--text-tertiary)" }}>Total Duration: </span>
            <span style={{ fontWeight: 600 }}>{Math.round(report.raw_observed_data.total_duration_seconds / 60)} min</span>
          </div>
          <div>
            <span style={{ color: "var(--text-tertiary)" }}>Foreground Events: </span>
            <span style={{ fontWeight: 600 }}>{report.raw_observed_data.event_count} events</span>
          </div>
          <div>
            <span style={{ color: "var(--text-tertiary)" }}>Top Applications: </span>
            <span style={{ fontWeight: 600 }}>{report.raw_observed_data.top_apps.join(", ")}</span>
          </div>
        </div>
      </div>

      {/* Evidence Citations */}
      {report.evidence_sessions && report.evidence_sessions.length > 0 && (
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap", fontSize: "0.78rem" }}>
          <span style={{ color: "var(--text-tertiary)", fontWeight: 600 }}>CITED EVIDENCE SESSIONS:</span>
          {report.evidence_sessions.map((sid) => (
            <SourceReference key={sid} sessionId={sid} />
          ))}
        </div>
      )}
    </div>
  );
};
