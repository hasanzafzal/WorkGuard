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
    <div className="glass-panel" style={{ padding: "20px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <span style={{ fontSize: "0.78rem", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.02em" }}>
          {title}
        </span>
        <div
          style={{
            width: "32px",
            height: "32px",
            borderRadius: "8px",
            backgroundColor: iconBg,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: iconColor,
          }}
        >
          <Icon size={17} />
        </div>
      </div>
      <div style={{ fontSize: "1.85rem", fontWeight: 700, margin: "10px 0 4px 0", letterSpacing: "-0.03em" }}>
        {value}
      </div>
      {(subtitle || badgeText) && (
        <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.75rem", color: "var(--text-tertiary)" }}>
          {badgeText && (
            <span className={`badge badge-${badgeColor}`} style={{ fontSize: "0.68rem", padding: "1px 6px" }}>
              {badgeText}
            </span>
          )}
          {subtitle && <span>{subtitle}</span>}
        </div>
      )}
    </div>
  );
};
