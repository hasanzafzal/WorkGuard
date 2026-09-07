import React from "react";
import { useLocation } from "react-router-dom";
import { Radio } from "lucide-react";

interface TopBarProps {
  isAutoRefresh: boolean;
  setIsAutoRefresh: (auto: boolean) => void;
  lastUpdated: string | null;
}

export const TopBar: React.FC<TopBarProps> = ({
  isAutoRefresh,
  setIsAutoRefresh,
  lastUpdated,
}) => {
  const location = useLocation();

  const getPageTitle = (path: string) => {
    if (path === "/") return { title: "Workforce Dashboard", subtitle: "Real-time workstation activity & telemetry", category: "Workspace" };
    if (path.startsWith("/employees/")) return { title: "Employee Profile", subtitle: "Workstation history & behavioral analytics", category: "Workspace" };
    if (path.startsWith("/employees")) return { title: "Employees Directory", subtitle: "Monitored endpoints & status", category: "Workspace" };
    if (path.startsWith("/sessions/")) return { title: "Session Package Details", subtitle: "Chronological event timeline & focus metrics", category: "Workspace" };
    if (path.startsWith("/sessions")) return { title: "Sessions Registry", subtitle: "Encrypted work-session telemetry packages", category: "Workspace" };
    if (path.startsWith("/security")) return { title: "Security Operations Center", subtitle: "Integrity validation & anomaly detections", category: "Intelligence" };
    if (path.startsWith("/reports")) return { title: "AI Intelligence Reports", subtitle: "LangGraph agent synthesis & evidence citations", category: "Intelligence" };
    if (path.startsWith("/chat")) return { title: "WorkGuard Copilot", subtitle: "Conversational RAG telemetry assistant", category: "Intelligence" };
    if (path.startsWith("/system")) return { title: "System Infrastructure", subtitle: "Services health, vector store & LLM", category: "Infrastructure" };
    return { title: "Admin Console", subtitle: "Enterprise monitoring system", category: "Admin" };
  };

  const { title, subtitle, category } = getPageTitle(location.pathname);

  return (
    <header
      style={{
        height: "60px",
        minHeight: "60px",
        padding: "0 24px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        borderBottom: "1px solid var(--border-separator)",
        backgroundColor: "var(--system-surface)",
        backdropFilter: "var(--glass-blur)",
        WebkitBackdropFilter: "var(--glass-blur)",
        zIndex: 10,
        position: "sticky",
        top: 0,
      }}
    >
      {/* Title & macOS Breadcrumb */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span
              style={{
                fontSize: "0.68rem",
                fontWeight: 600,
                color: "var(--text-tertiary)",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
              }}
            >
              {category}
            </span>
            <span style={{ color: "var(--text-quaternary)", fontSize: "0.65rem" }}>/</span>
            <h1
              style={{
                fontSize: "1.02rem",
                fontWeight: 700,
                margin: 0,
                letterSpacing: "-0.02em",
                color: "var(--text-primary)",
              }}
            >
              {title}
            </h1>
          </div>
          <p
            style={{
              fontSize: "0.72rem",
              color: "var(--text-secondary)",
              margin: 0,
              lineHeight: 1.2,
            }}
          >
            {subtitle}
          </p>
        </div>
      </div>

      {/* Sync and Refresh Controls */}
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        {lastUpdated && (
          <div
            style={{
              fontSize: "0.72rem",
              color: "var(--text-tertiary)",
              display: "flex",
              alignItems: "center",
              gap: "5px",
              padding: "4px 8px",
              borderRadius: "6px",
              backgroundColor: "rgba(0, 0, 0, 0.02)",
            }}
          >
            <Radio size={11} color="var(--apple-green)" />
            <span>
              Updated {new Date(lastUpdated).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
            </span>
          </div>
        )}

        {/* Auto Refresh Toggle - Apple Segmented Style */}
        <div className="apple-segmented-control">
          <button
            onClick={() => setIsAutoRefresh(true)}
            className={`apple-segmented-btn ${isAutoRefresh ? "active" : ""}`}
            style={{ padding: "4px 8px", fontSize: "0.72rem" }}
            title="Auto-refreshing every 5 seconds"
          >
            <span
              style={{
                width: "6px",
                height: "6px",
                borderRadius: "50%",
                backgroundColor: isAutoRefresh ? "var(--apple-green)" : "var(--apple-gray)",
                display: "inline-block",
              }}
            />
            <span>Live</span>
          </button>
          <button
            onClick={() => setIsAutoRefresh(false)}
            className={`apple-segmented-btn ${!isAutoRefresh ? "active" : ""}`}
            style={{ padding: "4px 8px", fontSize: "0.72rem" }}
            title="Auto-refresh paused"
          >
            <span>Paused</span>
          </button>
        </div>
      </div>
    </header>
  );
};
