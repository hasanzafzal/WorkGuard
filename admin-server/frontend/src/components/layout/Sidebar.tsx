import React from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  Layers,
  ShieldAlert,
  Sparkles,
  Bot,
  Sun,
  Moon,
  ShieldCheck,
  Server,
} from "lucide-react";

interface SidebarProps {
  serverOnline: boolean;
  theme: "light" | "dark";
  toggleTheme: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  serverOnline,
  theme,
  toggleTheme,
}) => {
  const navItems = [
    { to: "/", label: "Dashboard", icon: LayoutDashboard },
    { to: "/employees", label: "Employees", icon: Users },
    { to: "/sessions", label: "Sessions", icon: Layers },
    { to: "/security", label: "Security", icon: ShieldAlert },
    { to: "/reports", label: "AI Reports", icon: Sparkles },
    { to: "/chat", label: "WorkGuard Copilot", icon: Bot },
    { to: "/system", label: "System Status", icon: Server },
  ];

  return (
    <aside
      className="glass-sidebar"
      style={{
        width: "250px",
        minWidth: "250px",
        display: "flex",
        flexDirection: "column",
        borderRight: "1px solid var(--border-separator)",
        height: "100vh",
        position: "sticky",
        top: 0,
        zIndex: 20,
      }}
    >
      {/* Brand Header */}
      <div
        style={{
          padding: "20px 20px 16px 20px",
          borderBottom: "1px solid var(--border-separator)",
          display: "flex",
          alignItems: "center",
          gap: "10px",
        }}
      >
        <div
          style={{
            width: "32px",
            height: "32px",
            borderRadius: "9px",
            backgroundColor: "var(--apple-blue)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#FFF",
            boxShadow: "0 2px 8px rgba(0, 122, 255, 0.4)",
          }}
        >
          <ShieldCheck size={18} />
        </div>
        <div>
          <span style={{ fontSize: "0.95rem", fontWeight: 700, letterSpacing: "-0.01em" }}>
            WorkGuard
          </span>
          <span
            style={{
              display: "block",
              fontSize: "0.68rem",
              color: "var(--text-tertiary)",
              fontWeight: 500,
              textTransform: "uppercase",
              letterSpacing: "0.04em",
            }}
          >
            Admin Console
          </span>
        </div>
      </div>

      {/* Navigation List */}
      <nav
        style={{
          flex: 1,
          padding: "16px 12px",
          display: "flex",
          flexDirection: "column",
          gap: "4px",
          overflowY: "auto",
        }}
      >
        <div
          style={{
            fontSize: "0.68rem",
            fontWeight: 700,
            color: "var(--text-tertiary)",
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            padding: "4px 10px 8px 10px",
          }}
        >
          Analytics & Control
        </div>

        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `apple-sidebar-item ${isActive ? "active" : ""}`
              }
              style={{ textDecoration: "none" }}
            >
              <Icon size={16} />
              <span style={{ flex: 1 }}>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Footer System Status & Theme Toggle */}
      <div
        style={{
          padding: "14px 16px",
          borderTop: "1px solid var(--border-separator)",
          display: "flex",
          flexDirection: "column",
          gap: "10px",
          backgroundColor: "rgba(0, 0, 0, 0.02)",
        }}
      >
        {/* System Online Status */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            fontSize: "0.75rem",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <Server size={13} color="var(--text-secondary)" />
            <span style={{ color: "var(--text-secondary)" }}>LAN Server</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
            <span
              className="pulse-indicator"
              style={{
                backgroundColor: serverOnline ? "var(--apple-green)" : "var(--apple-red)",
              }}
            />
            <span
              style={{
                color: serverOnline ? "var(--apple-green)" : "var(--apple-red)",
                fontWeight: 600,
              }}
            >
              {serverOnline ? "Connected" : "Offline"}
            </span>
          </div>
        </div>

        {/* Theme Toggle Button */}
        <button
          onClick={toggleTheme}
          className="apple-btn apple-btn-secondary"
          style={{
            width: "100%",
            justifyContent: "center",
            padding: "6px",
            fontSize: "0.78rem",
          }}
          title="Toggle Light / Dark theme"
        >
          {theme === "dark" ? <Sun size={13} /> : <Moon size={13} />}
          <span>{theme === "dark" ? "Light Appearance" : "Dark Appearance"}</span>
        </button>
      </div>
    </aside>
  );
};
