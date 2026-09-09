import { request } from "./api";
import type { Session, SessionDetail } from "../types";

export const sessionApi = {
  async getSessions(params?: { search?: string; employee?: string; limit?: number }): Promise<Session[]> {
    let query = "?limit=" + (params?.limit || 100);
    if (params?.search) query += `&search=${encodeURIComponent(params.search)}`;
    if (params?.employee) query += `&employee=${encodeURIComponent(params.employee)}`;

    return request<Session[]>(`/api/v1/sessions${query}`, { method: "GET" });
  },

  async getSessionById(sessionId: string): Promise<SessionDetail> {
    return request<SessionDetail>(`/api/v1/sessions/${sessionId}`, { method: "GET" });
  },
};
