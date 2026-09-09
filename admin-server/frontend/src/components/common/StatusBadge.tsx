import React from "react";
import type { StatusType } from "../../types";


interface StatusBadgeProps {
  status: StatusType | string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const norm = status.toLowerCase();
  if (norm === "active") {
    return (
      <span className="badge badge-green">
        <span className="pulse-indicator" style={{ width: "5px", height: "5px" }} />
        Active
      </span>
    );
  }
  if (norm === "away") {
    return (
      <span className="badge badge-orange">
        Away
      </span>
    );
  }
  return (
    <span className="badge badge-gray">
      Inactive
    </span>
  );
};
