import React from "react";

interface LoadingStateProps {
  message?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = "Loading WorkGuard telemetry data...",
}) => {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "60px 20px",
        gap: "14px",
      }}
    >
      <div className="pulse-indicator" style={{ width: "16px", height: "16px" }} />
      <p style={{ color: "var(--text-secondary)", fontSize: "0.88rem" }}>{message}</p>
    </div>
  );
};
