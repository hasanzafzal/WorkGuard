import React, { useState, useEffect } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

export const Layout: React.FC = () => {
  const [serverOnline, setServerOnline] = useState(true);
  const [isAutoRefresh, setIsAutoRefresh] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string | null>(new Date().toISOString());

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

  const checkHealth = async () => {
    setIsLoading(true);
    try {
      const res = await fetch("/health");
      setServerOnline(res.ok);
      setLastUpdated(new Date().toISOString());
    } catch {
      setServerOnline(false);
    } finally {
      setIsLoading(false);
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
    <div style={{ display: "flex", minHeight: "100vh", backgroundColor: "var(--system-bg)" }}>
      {/* Sidebar Navigation */}
      <Sidebar
        serverOnline={serverOnline}
        theme={theme}
        toggleTheme={toggleTheme}
      />

      {/* Main Administrative Content Area */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <TopBar
          isAutoRefresh={isAutoRefresh}
          setIsAutoRefresh={setIsAutoRefresh}
          onManualRefresh={checkHealth}
          isLoading={isLoading}
          lastUpdated={lastUpdated}
        />

        <main style={{ flex: 1, overflowY: "auto" }}>
          <Outlet />
        </main>
      </div>
    </div>
  );
};
