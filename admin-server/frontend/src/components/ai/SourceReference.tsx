import React from "react";
import { Link } from "react-router-dom";
import { ExternalLink, Layers } from "lucide-react";

interface SourceReferenceProps {
  sessionId: string;
}

export const SourceReference: React.FC<SourceReferenceProps> = ({ sessionId }) => {
  return (
    <Link
      to={`/sessions/${sessionId}`}
      className="badge badge-blue"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "5px",
        padding: "3px 9px",
        textDecoration: "none",
        fontFamily: "monospace",
        fontSize: "0.75rem",
        borderRadius: "var(--radius-pill)",
        transition: "all var(--transition-fast)",
      }}
      title={`Inspect cited session evidence: ${sessionId}`}
    >
      <Layers size={11} />
      <span>{sessionId}</span>
      <ExternalLink size={10} />
    </Link>
  );
};
