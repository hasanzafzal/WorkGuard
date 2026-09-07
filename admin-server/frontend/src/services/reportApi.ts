import { request } from "./api";
import type { AIReport } from "../types";

export const reportApi = {
  async getReports(): Promise<AIReport[]> {
    return request<AIReport[]>("/api/v1/reports", { method: "GET" });
  },

  async getReportById(reportId: string): Promise<AIReport> {
    return request<AIReport>(`/api/v1/reports/${reportId}`, { method: "GET" });
  },
};
