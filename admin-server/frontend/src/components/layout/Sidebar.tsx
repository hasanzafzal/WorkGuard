import React, { useState } from "react";
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
  Search,
  PanelLeftClose,
  PanelLeftOpen,
  X,
} from "lucide-react";

interface SidebarProps {
  serverOnline: boolean;
  theme: "light" | "dark";
  toggleTheme: () => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

interface NavItemConfig {
  to: string;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  iconClass: string;
  badge?: {
    text: string;
    color: "green" | "red" | "indigo" | "blue";
  };
}

interface NavGroupConfig {
  title: string;
  items: NavItemConfig[];
}

export const Sidebar: React.FC<SidebarProps> = ({
  serverOnline,
  theme,
  toggleTheme,
  isCollapsed = false,
  onToggleCollapse,
}) => {
  const [searchQuery, setSearchQuery] = useState("");

  const navigationGroups: NavGroupConfig[] = [
    {
      title: "Workspace",
      items: [
        {
          to: "/",
          label: "Dashboard",
          icon: LayoutDashboard,
          iconClass: "icon-squircle-blue",
          badge: { text: "Live", color: "green" },
        },
        {
          to: "/employees",
          label: "Employees",
          icon: Users,
          iconClass: "icon-squircle-green",
        },
        {
          to: "/sessions",
          label: "Sessions",
          icon: Layers,
          iconClass: "icon-squircle-teal",
        },
      ],
    },
    {
      title: "Intelligence & Sec",
      items: [
        {
          to: "/security",
          label: "Security SOC",
          icon: ShieldAlert,
          iconClass: "icon-squircle-red",
          badge: { text: "Active", color: "red" },
        },
        {
          to: "/reports",
          label: "AI Reports",
          icon: Sparkles,
          iconClass: "icon-squircle-purple",
        },
        {
          to: "/chat",
          label: "WorkGuard Copilot",
          icon: Bot,
          iconClass: "icon-squircle-indigo",
          badge: { text: "AI", color: "indigo" },
        },
      ],
    },
    {
      title: "Infrastructure",
      items: [
        {
          to: "/system",
          label: "System Status",
          icon: Server,
          iconClass: "icon-squircle-gray",
        },
      ],
    },
  ];

  // Filter items based on quick search
  const filteredGroups = navigationGroups
    .map((group) => ({
      ...group,
      items: group.items.filter((item) =>
        item.label.toLowerCase().includes(searchQuery.toLowerCase())
      ),
    }))
    .filter((group) => group.items.length > 0);

  return (
    <aside
      className="glass-sidebar"
      style={{
        width: isCollapsed ? "74px" : "260px",
        minWidth: isCollapsed ? "74px" : "260px",
        display: "flex",
        flexDirection: "column",
        borderRight: "1px solid var(--border-separator)",
        height: "100vh",
        maxHeight: "100vh",
        position: "sticky",
        top: 0,
        zIndex: 20,
        userSelect: "none",
        overflow: "hidden",
        flexShrink: 0,
      }}
    >
      {/* Brand Identity Header */}
      <div
        style={{
          padding: isCollapsed ? "14px 6px" : "14px 16px",
          display: "flex",
          flexDirection: isCollapsed ? "column" : "row",
          alignItems: "center",
          justifyContent: isCollapsed ? "center" : "space-between",
          gap: isCollapsed ? "10px" : "10px",
          borderBottom: "1px solid var(--border-separator)",
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px", overflow: "hidden" }}>
          <div
            style={{
              width: "34px",
              height: "34px",
              borderRadius: "9px",
              background: "linear-gradient(135deg, #007AFF 0%, #0051B3 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#FFFFFF",
              boxShadow: "0 3px 10px rgba(0, 122, 255, 0.35)",
              flexShrink: 0,
            }}
            title="WorkGuard Admin Console"
          >
            <ShieldCheck size={19} />
          </div>

          {!isCollapsed && (
            <div style={{ overflow: "hidden" }}>
              <span
                style={{
                  fontSize: "0.95rem",
                  fontWeight: 700,
                  letterSpacing: "-0.02em",
                  color: "var(--text-primary)",
                  display: "block",
                  lineHeight: 1.2,
                }}
              >
                WorkGuard
              </span>
              <span
                style={{
                  display: "block",
                  fontSize: "0.68rem",
                  color: "var(--text-tertiary)",
                  fontWeight: 500,
                  letterSpacing: "0.02em",
                }}
              >
                Admin Console
              </span>
            </div>
          )}
        </div>

        {/* Sidebar Collapse Toggle Button */}
        {onToggleCollapse && (
          <button
            onClick={onToggleCollapse}
            className="apple-btn apple-btn-subtle"
            style={{
              padding: "4px",
              borderRadius: "6px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
            title={isCollapsed ? "Expand Sidebar (⌘B)" : "Collapse Sidebar (⌘B)"}
          >
            {isCollapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={15} />}
          </button>
        )}
      </div>

      {/* 3. Quick Search Filter (Expanded only) */}
      {!isCollapsed && (
        <div style={{ padding: "10px 14px 6px 14px" }}>
          <div className="apple-search-bar">
            <Search size={13} color="var(--text-tertiary)" />
            <input
              type="text"
              placeholder="Filter views..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                style={{
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  display: "flex",
                  color: "var(--text-tertiary)",
                  padding: 0,
                }}
              >
                <X size={12} />
              </button>
            )}
          </div>
        </div>
      )}

      {/* 4. Navigation Links */}
      <nav
        style={{
          flex: 1,
          padding: isCollapsed ? "10px 6px" : "8px 10px",
          display: "flex",
          flexDirection: "column",
          gap: isCollapsed ? "6px" : "10px",
          overflow: "hidden",
        }}
      >
        {filteredGroups.map((group) => (
          <div key={group.title}>
            {!isCollapsed && (
              <div
                style={{
                  fontSize: "0.65rem",
                  fontWeight: 700,
                  color: "var(--text-tertiary)",
                  textTransform: "uppercase",
                  letterSpacing: "0.07em",
                  padding: "4px 8px 6px 8px",
                }}
              >
                {group.title}
              </div>
            )}

            <div style={{ display: "flex", flexDirection: "column", gap: "3px" }}>
              {group.items.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === "/"}
                    className={({ isActive }) =>
                      `apple-sidebar-item ${isActive ? "active" : ""}`
                    }
                    title={isCollapsed ? item.label : undefined}
                    style={{
                      justifyContent: isCollapsed ? "center" : "flex-start",
                      padding: isCollapsed ? "8px 0" : "6px 10px",
                    }}
                  >
                    <div className={`apple-icon-squircle ${item.iconClass}`}>
                      <Icon size={15} />
                    </div>

                    {!isCollapsed && (
                      <span
                        style={{
                          flex: 1,
                          fontSize: "0.83rem",
                          letterSpacing: "-0.01em",
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                      >
                        {item.label}
                      </span>
                    )}

                    {!isCollapsed && item.badge && (
                      <span
                        className={`badge badge-${item.badge.color}`}
                        style={{
                          fontSize: "0.64rem",
                          padding: "1px 6px",
                          borderRadius: "6px",
                        }}
                      >
                        {item.badge.text}
                      </span>
                    )}
                  </NavLink>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* 5. Footer Control Center & System Status */}
      <div
        style={{
          padding: isCollapsed ? "10px 6px" : "12px 14px",
          borderTop: "1px solid var(--border-separator)",
          display: "flex",
          flexDirection: "column",
          gap: "8px",
          background: "rgba(0, 0, 0, 0.02)",
          flexShrink: 0,
        }}
      >
        {/* Apple Segmented Theme Switcher */}
        {!isCollapsed ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <div className="apple-segmented-control" style={{ width: "100%" }}>
              <button
                onClick={() => theme !== "light" && toggleTheme()}
                className={`apple-segmented-btn ${theme === "light" ? "active" : ""}`}
                style={{ flex: 1 }}
              >
                <Sun size={12} />
                <span>Light</span>
              </button>
              <button
                onClick={() => theme !== "dark" && toggleTheme()}
                className={`apple-segmented-btn ${theme === "dark" ? "active" : ""}`}
                style={{ flex: 1 }}
              >
                <Moon size={12} />
                <span>Dark</span>
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={toggleTheme}
            className="apple-btn apple-btn-secondary"
            style={{
              padding: "8px",
              borderRadius: "8px",
              justifyContent: "center",
              width: "100%",
            }}
            title={`Switch to ${theme === "dark" ? "Light" : "Dark"} Mode`}
          >
            {theme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
          </button>
        )}

        {/* LAN Server Health Card */}
        {!isCollapsed ? (
          <div
            style={{
              padding: "8px 10px",
              borderRadius: "8px",
              backgroundColor: "var(--system-grouped-bg)",
              border: "1px solid var(--border-subtle)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              fontSize: "0.72rem",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <Server size={12} color="var(--text-secondary)" />
              <span style={{ color: "var(--text-secondary)", fontWeight: 500 }}>
                LAN Server
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
              <span
                className="pulse-indicator"
                style={{
                  backgroundColor: serverOnline ? "var(--apple-green)" : "var(--apple-red)",
                  width: "6px",
                  height: "6px",
                }}
              />
              <span
                style={{
                  color: serverOnline ? "var(--apple-green)" : "var(--apple-red)",
                  fontWeight: 600,
                }}
              >
                {serverOnline ? "Online" : "Offline"}
              </span>
            </div>
          </div>
        ) : (
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              padding: "4px 0",
            }}
            title={serverOnline ? "LAN Server Online" : "LAN Server Offline"}
          >
            <span
              className="pulse-indicator"
              style={{
                backgroundColor: serverOnline ? "var(--apple-green)" : "var(--apple-red)",
                width: "8px",
                height: "8px",
              }}
            />
          </div>
        )}
      </div>
    </aside>
  );
};
