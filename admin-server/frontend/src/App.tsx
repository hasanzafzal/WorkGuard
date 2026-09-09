import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "./components/layout/Layout";
import { Dashboard } from "./pages/Dashboard";
import { Employees } from "./pages/Employees";
import { EmployeeDetails } from "./pages/EmployeeDetails";
import { Sessions } from "./pages/Sessions";
import { SessionDetails } from "./pages/SessionDetails";
import { Security } from "./pages/Security";
import { Reports } from "./pages/Reports";
import { Chat } from "./pages/Chat";
import { SystemStatus } from "./pages/SystemStatus";

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="employees" element={<Employees />} />
          <Route path="employees/:employeeId" element={<EmployeeDetails />} />
          <Route path="sessions" element={<Sessions />} />
          <Route path="sessions/:sessionId" element={<SessionDetails />} />
          <Route path="security" element={<Security />} />
          <Route path="reports" element={<Reports />} />
          <Route path="chat" element={<Chat />} />
          <Route path="system" element={<SystemStatus />} />
          {/* Catch-all redirect to dashboard */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
