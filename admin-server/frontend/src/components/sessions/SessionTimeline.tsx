import React from "react";
import { Clock } from "lucide-react";
import type { SessionEvent } from "../../types";


interface SessionTimelineProps {
  events: SessionEvent[];
}

export const SessionTimeline: React.FC<SessionTimelineProps> = ({ events }) => {
  if (!events || events.length === 0) {
    return (
      <div style={{ padding: "20px", color: "var(--text-tertiary)", fontSize: "0.85rem" }}>
        No event sequence recorded in this session.
      </div>
    );
  }

  const getEventBadge = (eventType: string) => {
    switch (eventType) {
      case "focused":
        return <span className="badge badge-green">Focused</span>;
      case "unfocused":
        return <span className="badge badge-gray">Unfocused</span>;
      case "file_system":
        return <span className="badge badge-orange">File I/O</span>;
      default:
        return <span className="badge badge-blue">Process</span>;
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
      {events.map((evt, idx) => (
        <div
          key={idx}
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: "14px",
            padding: "10px 14px",
            borderRadius: "var(--radius-md)",
            backgroundColor: "var(--system-grouped-bg)",
            border: "1px solid var(--border-subtle)",
            fontSize: "0.82rem",
          }}
        >
          {/* Timestamp Pill */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "4px",
              fontFamily: "monospace",
              fontWeight: 600,
              color: "var(--text-secondary)",
              minWidth: "75px",
            }}
          >
            <Clock size={13} />
            <span>{evt.timestamp}</span>
          </div>

          {/* Event description */}
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontWeight: 700, color: "var(--text-primary)" }}>
                {evt.app_name}
              </span>
              {getEventBadge(evt.event_type)}
              {evt.active_seconds && (
                <span style={{ fontSize: "0.75rem", color: "var(--text-tertiary)" }}>
                  ({evt.active_seconds}s active)
                </span>
              )}
            </div>
            {evt.window_title && (
              <p style={{ color: "var(--text-secondary)", fontSize: "0.78rem", marginTop: "3px" }}>
                {evt.window_title}
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};
