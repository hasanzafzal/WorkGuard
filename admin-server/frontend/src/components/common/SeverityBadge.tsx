import React from "react";
import { AlertOctagon, AlertTriangle, AlertCircle, Info } from "lucide-react";
import type { SeverityType } from "../../types";


interface SeverityBadgeProps {
  severity: SeverityType | string;
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({ severity }) => {
  const norm = severity.toUpperCase();
  switch (norm) {
    case "CRITICAL":
      return (
        <span className="badge badge-red" style={{ fontWeight: 700 }}>
          <AlertOctagon size={12} />
          CRITICAL
        </span>
      );
    case "HIGH":
      return (
        <span className="badge badge-red">
          <AlertTriangle size={12} />
          HIGH
        </span>
      );
    case "MEDIUM":
      return (
        <span className="badge badge-orange">
          <AlertCircle size={12} />
          MEDIUM
        </span>
      );
    case "LOW":
    default:
      return (
        <span className="badge badge-blue">
          <Info size={12} />
          LOW
        </span>
      );
  }
};
