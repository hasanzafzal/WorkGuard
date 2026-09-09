import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Search, ShieldAlert, ArrowRight } from "lucide-react";
import { employeeApi } from "../services/employeeApi";
import type { Employee } from "../types";

import { StatusBadge } from "../components/common/StatusBadge";
import { LoadingState } from "../components/common/LoadingState";
import { ErrorState } from "../components/common/ErrorState";
import { EmptyState } from "../components/common/EmptyState";

export const Employees: React.FC = () => {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const loadEmployees = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await employeeApi.getEmployees();
      setEmployees(data);
    } catch (err: any) {
      setError(err.message || "Failed to load employees.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEmployees();
  }, []);

  if (loading) return <LoadingState message="Loading workforce directory..." />;
  if (error) return <ErrorState message={error} onRetry={loadEmployees} />;

  const filtered = employees.filter((emp) => {
    const matchesSearch =
      emp.employee_name.toLowerCase().includes(search.toLowerCase()) ||
      emp.employee_id.toLowerCase().includes(search.toLowerCase());

    const matchesStatus =
      statusFilter === "all" || emp.status.toLowerCase() === statusFilter.toLowerCase();

    return matchesSearch && matchesStatus;
  });

  const formatHours = (seconds: number) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${hrs}h ${mins}m`;
  };

  return (
    <div style={{ padding: "28px", display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Search & Filter Header */}
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
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div
            style={{
              position: "relative",
              width: "320px",
            }}
          >
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
              placeholder="Search employee name or system ID..."
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

          <div style={{ display: "flex", gap: "6px" }}>
            {["all", "active", "away", "inactive"].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className="badge"
                style={{
                  border: "none",
                  cursor: "pointer",
                  padding: "5px 12px",
                  backgroundColor: statusFilter === st ? "var(--apple-blue)" : "var(--system-grouped-bg)",
                  color: statusFilter === st ? "#FFF" : "var(--text-secondary)",
                }}
              >
                {st.charAt(0).toUpperCase() + st.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div style={{ fontSize: "0.82rem", color: "var(--text-secondary)" }}>
          Showing <strong>{filtered.length}</strong> of {employees.length} employees
        </div>
      </div>

      {/* Employees Table */}
      {filtered.length === 0 ? (
        <EmptyState
          title="No employees found"
          description="Try changing your search terms or filter selection."
        />
      ) : (
        <div className="glass-panel" style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border-subtle)", backgroundColor: "var(--system-grouped-bg)", textAlign: "left" }}>
                  <th style={{ padding: "12px 16px", color: "var(--text-tertiary)", fontWeight: 600 }}>EMPLOYEE ID</th>
                  <th style={{ padding: "12px 16px", color: "var(--text-tertiary)", fontWeight: 600 }}>EMPLOYEE NAME</th>
                  <th style={{ padding: "12px 16px", color: "var(--text-tertiary)", fontWeight: 600 }}>SESSIONS</th>
                  <th style={{ padding: "12px 16px", color: "var(--text-tertiary)", fontWeight: 600 }}>TOTAL ACTIVE TIME</th>
                  <th style={{ padding: "12px 16px", color: "var(--text-tertiary)", fontWeight: 600 }}>LAST ACTIVITY</th>
                  <th style={{ padding: "12px 16px", color: "var(--text-tertiary)", fontWeight: 600 }}>STATUS</th>
                  <th style={{ padding: "12px 16px", color: "var(--text-tertiary)", fontWeight: 600 }}>ALERTS</th>
                  <th style={{ padding: "12px 16px", color: "var(--text-tertiary)", fontWeight: 600, textAlign: "right" }}>DETAILS</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((emp) => (
                  <tr
                    key={emp.employee_id}
                    style={{
                      borderBottom: "1px solid var(--border-separator)",
                      transition: "background var(--transition-fast)",
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "var(--apple-blue-subtle)")}
                    onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
                  >
                    <td style={{ padding: "12px 16px", fontFamily: "monospace", color: "var(--text-secondary)" }}>
                      {emp.employee_id}
                    </td>
                    <td style={{ padding: "12px 16px", fontWeight: 600 }}>
                      <Link
                        to={`/employees/${emp.employee_id}`}
                        style={{ color: "var(--text-primary)", textDecoration: "none" }}
                      >
                        {emp.employee_name}
                      </Link>
                    </td>
                    <td style={{ padding: "12px 16px" }}>{emp.sessions_count}</td>
                    <td style={{ padding: "12px 16px" }}>{formatHours(emp.total_active_time_seconds)}</td>
                    <td style={{ padding: "12px 16px", color: "var(--text-secondary)", fontSize: "0.8rem" }}>
                      {new Date(emp.last_activity).toLocaleString([], {
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </td>
                    <td style={{ padding: "12px 16px" }}>
                      <StatusBadge status={emp.status} />
                    </td>
                    <td style={{ padding: "12px 16px" }}>
                      {emp.security_alert_count > 0 ? (
                        <span className="badge badge-red">
                          <ShieldAlert size={12} />
                          {emp.security_alert_count} Flagged
                        </span>
                      ) : (
                        <span className="badge badge-green">0 Alerts</span>
                      )}
                    </td>
                    <td style={{ padding: "12px 16px", textAlign: "right" }}>
                      <Link
                        to={`/employees/${emp.employee_id}`}
                        className="apple-btn apple-btn-secondary"
                        style={{ padding: "4px 10px", fontSize: "0.75rem" }}
                      >
                        <span>Profile</span>
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
