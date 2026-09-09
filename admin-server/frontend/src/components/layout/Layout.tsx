import React, { useState, useEffect } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

export const Layout: React.FC = () => {
  const [serverOnline, setServerOnline] = useState(true);
  const [isAutoRefresh, setIsAutoRefresh] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<string | null>(new Date().toISOString());

  // Sidebar collapse state
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(() => {
    return localStorage.getItem("workguard-sidebar-collapsed") === "true";
  });

  const toggleSidebar = () => {
    setIsSidebarCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem("workguard-sidebar-collapsed", String(next));
      return next;
    });
  };

  // Theme support
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    return (localStorage.getItem("workguard-theme") as "light" | "dark") || "dark";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("workguard-theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  };

  // Keyboard shortcut: Cmd/Ctrl + B to toggle sidebar
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "b") {
        e.preventDefault();
        toggleSidebar();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const checkHealth = async () => {
    try {
      const res = await fetch("/health");
      setServerOnline(res.ok);
      setLastUpdated(new Date().toISOString());
    } catch {
      setServerOnline(false);
    }
  };

  useEffect(() => {
    checkHealth();
  }, []);

  useEffect(() => {
    if (!isAutoRefresh) return;
    const interval = setInterval(checkHealth, 5000);
    return () => clearInterval(interval);
  }, [isAutoRefresh]);

  return (
    <div
      style={{
        display: "flex",
        height: "100vh",
        maxHeight: "100vh",
        backgroundColor: "var(--system-bg)",
        overflow: "hidden",
      }}
    >
      {/* macOS Frosted Sidebar Navigation */}
      <Sidebar
        serverOnline={serverOnline}
        theme={theme}
        toggleTheme={toggleTheme}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={toggleSidebar}
      />

      {/* Main Administrative Window Area */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          minWidth: 0,
          height: "100vh",
          maxHeight: "100vh",
          overflow: "hidden",
          position: "relative",
        }}
      >
        <TopBar
          isAutoRefresh={isAutoRefresh}
          setIsAutoRefresh={setIsAutoRefresh}
          lastUpdated={lastUpdated}
        />

        <main
          style={{
            flex: 1,
            overflowY: "auto",
            backgroundColor: "var(--system-bg)",
            minHeight: 0,
          }}
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
};
