import React from "react";
import { useLocation } from "react-router-dom";
import { RefreshCw, Radio } from "lucide-react";

interface TopBarProps {
  isAutoRefresh: boolean;
  setIsAutoRefresh: (auto: boolean) => void;
  onManualRefresh: () => void;
  isLoading: boolean;
  lastUpdated: string | null;
}

export const TopBar: React.FC<TopBarProps> = ({
  isAutoRefresh,
  setIsAutoRefresh,
  onManualRefresh,
  isLoading,
  lastUpdated,
}) => {
  const location = useLocation();

  const getPageTitle = (path: string) => {
    if (path === "/") return { title: "Workforce Dashboard", subtitle: "Real-time workstation activity & telemetry" };
    if (path.startsWith("/employees/")) return { title: "Employee Profile", subtitle: "Workstation history & behavioral analytics" };
    if (path.startsWith("/employees")) return { title: "Employees Directory", subtitle: "Monitored endpoints & status" };
    if (path.startsWith("/sessions/")) return { title: "Session Package Details", subtitle: "Chronological event timeline & focus metrics" };
    if (path.startsWith("/sessions")) return { title: "Sessions Registry", subtitle: "Encrypted work-session telemetry packages" };
    if (path.startsWith("/security")) return { title: "Security Operations Center", subtitle: "Integrity validation & anomaly detections" };
    if (path.startsWith("/reports")) return { title: "AI Intelligence Reports", subtitle: "LangGraph agent synthesis & evidence citations" };
    if (path.startsWith("/chat")) return { title: "WorkGuard Copilot", subtitle: "Conversational RAG telemetry assistant" };
    return { title: "Admin Console", subtitle: "Enterprise monitoring system" };
  };

  const { title, subtitle } = getPageTitle(location.pathname);

  return (
    <header
      className="glass-panel"
      style={{
        height: "64px",
        minHeight: "64px",
        padding: "0 28px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        borderBottom: "1px solid var(--border-separator)",
        borderRadius: 0,
        backgroundColor: "var(--system-chrome)",
        zIndex: 10,
        position: "sticky",
        top: 0,
      }}
    >
      {/* Title & Subtitle */}
      <div>
        <h1 style={{ fontSize: "1.1rem", fontWeight: 700, margin: 0 }}>{title}</h1>
        <p style={{ fontSize: "0.72rem", color: "var(--text-tertiary)", margin: 0 }}>{subtitle}</p>
      </div>

      {/* Sync and Refresh Controls */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        {lastUpdated && (
          <div style={{ fontSize: "0.72rem", color: "var(--text-tertiary)", display: "flex", alignItems: "center", gap: "6px" }}>
            <Radio size={12} color="var(--apple-green)" />
            <span>Updated {new Date(lastUpdated).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</span>
          </div>
        )}

        {/* Auto Refresh Toggle */}
        <button
          onClick={() => setIsAutoRefresh(!isAutoRefresh)}
          className={`apple-btn ${isAutoRefresh ? "apple-btn-secondary" : "apple-btn-subtle"}`}
          style={{ fontSize: "0.75rem", padding: "5px 10px" }}
          title={isAutoRefresh ? "Auto-refreshing every 5s" : "Auto-refresh paused"}
        >
          <span
            style={{
              width: "6px",
              height: "6px",
              borderRadius: "50%",
              backgroundColor: isAutoRefresh ? "var(--apple-green)" : "var(--apple-gray)",
            }}
          />
          <span>{isAutoRefresh ? "Live 5s" : "Manual"}</span>
        </button>

        {/* Refresh Button */}
        <button
          onClick={onManualRefresh}
          disabled={isLoading}
          className="apple-btn apple-btn-secondary"
          style={{ fontSize: "0.75rem", padding: "5px 10px" }}
          title="Manual refresh"
        >
          <RefreshCw size={13} className={isLoading ? "pulse-indicator" : ""} />
          <span>Refresh</span>
        </button>
      </div>
    </header>
  );
};
