import { request } from "./api";
import type { DashboardData } from "../types";

export const dashboardApi = {
  async getDashboard(): Promise<DashboardData> {
    return request<DashboardData>("/api/v1/dashboard", { method: "GET" });
  },
};
