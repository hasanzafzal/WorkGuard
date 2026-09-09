import React from "react";
import { FolderSearch } from "lucide-react";

interface EmptyStateProps {
  title?: string;
  description?: string;
  actionText?: string;
  onAction?: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = "No Records Found",
  description = "There is currently no recorded telemetry matching your criteria.",
  actionText,
  onAction,
}) => {
  return (
    <div
      className="glass-panel"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "50px 24px",
        textAlign: "center",
        gap: "12px",
      }}
    >
      <FolderSearch size={40} color="var(--text-tertiary)" />
      <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>{title}</h3>
      <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem", maxWidth: "420px" }}>
        {description}
      </p>
      {actionText && onAction && (
        <button onClick={onAction} className="apple-btn apple-btn-primary" style={{ marginTop: "6px" }}>
          <span>{actionText}</span>
        </button>
      )}
    </div>
  );
};
