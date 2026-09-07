import React from "react";
import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  iconColor?: string;
  iconBg?: string;
  badgeText?: string;
  badgeColor?: "blue" | "green" | "orange" | "red" | "indigo";
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  iconColor = "var(--apple-blue)",
  iconBg = "var(--apple-blue-subtle)",
  badgeText,
  badgeColor = "blue",
}) => {
  return (
    <div
      className="glass-panel"
      style={{
        padding: "18px 20px",
        transition: "all var(--transition-fast)",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <span
          style={{
            fontSize: "0.72rem",
            fontWeight: 600,
            color: "var(--text-secondary)",
            textTransform: "uppercase",
            letterSpacing: "0.04em",
          }}
        >
          {title}
        </span>
        <div
          style={{
            width: "30px",
            height: "30px",
            borderRadius: "8px",
            backgroundColor: iconBg,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: iconColor,
            boxShadow: `0 2px 6px ${iconBg}`,
          }}
        >
          <Icon size={16} />
        </div>
      </div>
      <div
        style={{
          fontSize: "1.85rem",
          fontWeight: 700,
          margin: "10px 0 4px 0",
          letterSpacing: "-0.035em",
          color: "var(--text-primary)",
        }}
      >
        {value}
      </div>
      {(subtitle || badgeText) && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            fontSize: "0.74rem",
            color: "var(--text-tertiary)",
          }}
        >
          {badgeText && (
            <span
              className={`badge badge-${badgeColor}`}
              style={{ fontSize: "0.65rem", padding: "1px 7px" }}
            >
              {badgeText}
            </span>
          )}
          {subtitle && <span>{subtitle}</span>}
        </div>
      )}
    </div>
  );
};
