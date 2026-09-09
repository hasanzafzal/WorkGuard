import React from "react";
import type { AppUsageStat } from "../../types";


interface ApplicationUsageChartProps {
  data: AppUsageStat[] | Record<string, number>;
  title?: string;
}

export const ApplicationUsageChart: React.FC<ApplicationUsageChartProps> = ({
  data,
  title = "Application Usage Breakdown",
}) => {
  // Normalize data array
  let stats: AppUsageStat[] = [];
  if (Array.isArray(data)) {
    stats = data;
  } else if (typeof data === "object" && data !== null) {
    const total = Object.values(data).reduce((a, b) => a + b, 0) || 1;
    stats = Object.entries(data).map(([app_name, active_seconds]) => ({
      app_name,
      active_seconds,
      percentage: Math.round((active_seconds / total) * 100),
    }));
  }

  const formatDuration = (seconds: number) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    if (hrs > 0) return `${hrs}h ${mins}m`;
    if (mins > 0) return `${mins}m`;
    return `${seconds}s`;
  };

  const getBarColor = (index: number) => {
    const colors = [
      "var(--apple-blue)",
      "var(--apple-indigo)",
      "var(--apple-teal)",
      "var(--apple-green)",
      "var(--apple-orange)",
      "var(--apple-purple)",
    ];
    return colors[index % colors.length];
  };

  return (
    <div className="glass-panel" style={{ padding: "24px" }}>
      <h3 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: "16px" }}>{title}</h3>
      <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
        {stats.map((item, idx) => {
          const color = getBarColor(idx);
          return (
            <div key={item.app_name}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: "0.82rem",
                  marginBottom: "6px",
                }}
              >
                <span style={{ fontWeight: 600 }}>{item.app_name}</span>
                <div style={{ display: "flex", gap: "10px", color: "var(--text-secondary)" }}>
                  <span>{formatDuration(item.active_seconds)}</span>
                  <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                    {item.percentage}%
                  </span>
                </div>
              </div>
              <div
                style={{
                  height: "8px",
                  borderRadius: "4px",
                  backgroundColor: "var(--system-grouped-bg)",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    width: `${Math.min(item.percentage, 100)}%`,
                    height: "100%",
                    backgroundColor: color,
                    borderRadius: "4px",
                    transition: "width 0.4s ease",
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
