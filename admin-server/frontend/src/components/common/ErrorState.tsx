import React from "react";
import { AlertCircle, RefreshCw } from "lucide-react";

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  message = "Unable to load data from WorkGuard server.",
  onRetry,
}) => {
  return (
    <div
      className="glass-panel"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "48px 24px",
        textAlign: "center",
        gap: "12px",
        borderColor: "rgba(255, 59, 48, 0.2)",
      }}
    >
      <AlertCircle size={36} color="var(--apple-red)" />
      <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>Telemetry Load Error</h3>
      <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem", maxWidth: "400px" }}>
        {message}
      </p>
      {onRetry && (
        <button onClick={onRetry} className="apple-btn apple-btn-secondary" style={{ marginTop: "8px" }}>
          <RefreshCw size={14} />
          <span>Retry Connection</span>
        </button>
      )}
    </div>
  );
};
