import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Search, ArrowUpDown, ArrowRight } from "lucide-react";
import { sessionApi } from "../services/sessionApi";
import type { Session } from "../types";

import { LoadingState } from "../components/common/LoadingState";
import { ErrorState } from "../components/common/ErrorState";
import { EmptyState } from "../components/common/EmptyState";

export const Sessions: React.FC = () => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [employeeFilter, setEmployeeFilter] = useState("all");
  const [sortOrder, setSortOrder] = useState<"desc" | "asc">("desc");

  const loadSessions = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await sessionApi.getSessions();
      setSessions(data);
    } catch (err: any) {
      setError(err.message || "Failed to load sessions.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  if (loading) return <LoadingState message="Loading recorded work sessions..." />;
  if (error) return <ErrorState message={error} onRetry={loadSessions} />;

  const uniqueEmployees = Array.from(new Set(sessions.map((s) => s.employee_name)));

  const filtered = sessions
    .filter((s) => {
      const matchesSearch =
        s.session_id.toLowerCase().includes(search.toLowerCase()) ||
        s.employee_name.toLowerCase().includes(search.toLowerCase()) ||
        s.employee_id.toLowerCase().includes(search.toLowerCase());

      const matchesEmp = employeeFilter === "all" || s.employee_name === employeeFilter;

      return matchesSearch && matchesEmp;
    })
    .sort((a, b) => {
      const timeA = new Date(a.start_time).getTime();
      const timeB = new Date(b.start_time).getTime();
      return sortOrder === "desc" ? timeB - timeA : timeA - timeB;
    });

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  return (
    <div style={{ padding: "28px", display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Search & Filter Toolbar */}
      <div
        className="glass-panel"
        style={{
          padding: "16px 20px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "14px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flex: 1 }}>
          <div style={{ position: "relative", width: "300px" }}>
            <Search
              size={15}
              style={{
                position: "absolute",
                left: "12px",
                top: "50%",
                transform: "translateY(-50%)",
                color: "var(--text-tertiary)",
              }}
            />
            <input
              type="text"
              placeholder="Search session ID or employee..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{
                width: "100%",
                padding: "8px 12px 8px 34px",
                borderRadius: "var(--radius-pill)",
                border: "1px solid var(--border-subtle)",
                backgroundColor: "var(--system-grouped-bg)",
                color: "var(--text-primary)",
                fontSize: "0.82rem",
                outline: "none",
              }}
            />
          </div>

          {/* Employee Filter */}
          <select
            value={employeeFilter}
            onChange={(e) => setEmployeeFilter(e.target.value)}
            style={{
              padding: "7px 12px",
              borderRadius: "var(--radius-pill)",
              border: "1px solid var(--border-subtle)",
              backgroundColor: "var(--system-grouped-bg)",
              color: "var(--text-primary)",
              fontSize: "0.8rem",
              outline: "none",
            }}
          >
            <option value="all">All Employees</option>
            {uniqueEmployees.map((emp) => (
              <option key={emp} value={emp}>
                {emp}
              </option>
            ))}
          </select>

          {/* Sort Button */}
          <button
            onClick={() => setSortOrder((prev) => (prev === "desc" ? "asc" : "desc"))}
            className="apple-btn apple-btn-secondary"
            style={{ fontSize: "0.78rem", padding: "6px 12px" }}
          >
            <ArrowUpDown size={13} />
            <span>Time ({sortOrder === "desc" ? "Newest" : "Oldest"})</span>
          </button>
        </div>

        <div style={{ fontSize: "0.82rem", color: "var(--text-secondary)" }}>
          Showing <strong>{filtered.length}</strong> sessions
        </div>
      </div>

      {/* Sessions Table */}
      {filtered.length === 0 ? (
        <EmptyState
          title="No sessions found"
          description="Try broadening your search query or selecting 'All Employees'."
        />
      ) : (
        <div className="glass-panel" style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.84rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border-subtle)", backgroundColor: "var(--system-grouped-bg)", textAlign: "left" }}>
                  <th style={{ padding: "12px 16px", color: "var(--text-tertiary)", fontWeight: 600 }}>SESSION ID</th>
                  <th style={{ padding: "12px 16px", color: "var(--text-tertiary)", fontWeight: 600 }}>EMPLOYEE</th>
                  <th style={{ padding: "12px 16px", color: "var(--text-tertiary)", fontWeight: 600 }}>START TIME</th>
                  <th style={{ padding: "12px 16px", color: "var(--text-tertiary)", fontWeight: 600 }}>END TIME</th>
                  <th style={{ padding: "12px 16px", color: "var(--text-tertiary)", fontWeight: 600 }}>DURATION</th>
                  <th style={{ padding: "12px 16px", color: "var(--text-tertiary)", fontWeight: 600 }}>NUMBER OF EVENTS</th>
                  <th style={{ padding: "12px 16px", color: "var(--text-tertiary)", fontWeight: 600, textAlign: "right" }}>ACTION</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((s) => (
                  <tr
                    key={s.session_id}
                    style={{
                      borderBottom: "1px solid var(--border-separator)",
                      transition: "background var(--transition-fast)",
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "var(--apple-blue-subtle)")}
                    onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
                  >
                    <td style={{ padding: "12px 16px", fontFamily: "monospace", fontWeight: 600 }}>
                      <Link to={`/sessions/${s.session_id}`} style={{ color: "var(--apple-blue)", textDecoration: "none" }}>
                        {s.session_id}
                      </Link>
                    </td>
                    <td style={{ padding: "12px 16px", fontWeight: 600 }}>
                      <Link to={`/employees/${s.employee_id}`} style={{ color: "var(--text-primary)", textDecoration: "none" }}>
                        {s.employee_name}
                      </Link>
                    </td>
                    <td style={{ padding: "12px 16px", color: "var(--text-secondary)", fontSize: "0.8rem" }}>
                      {new Date(s.start_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                    </td>
                    <td style={{ padding: "12px 16px", color: "var(--text-secondary)", fontSize: "0.8rem" }}>
                      {new Date(s.end_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                    </td>
                    <td style={{ padding: "12px 16px" }}>
                      {formatDuration(s.duration_seconds)}
                    </td>
                    <td style={{ padding: "12px 16px" }}>
                      <span className="badge badge-gray">{s.events_count} events</span>
                    </td>
                    <td style={{ padding: "12px 16px", textAlign: "right" }}>
                      <Link
                        to={`/sessions/${s.session_id}`}
                        className="apple-btn apple-btn-secondary"
                        style={{ padding: "4px 10px", fontSize: "0.75rem" }}
                      >
                        <span>Details</span>
                        <ArrowRight size={12} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
