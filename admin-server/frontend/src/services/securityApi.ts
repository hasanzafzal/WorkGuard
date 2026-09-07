import { request } from "./api";
import type { SecurityEvent } from "../types";

export const securityApi = {
  async getSecurityEvents(): Promise<SecurityEvent[]> {
    return request<SecurityEvent[]>("/api/v1/security/events", { method: "GET" });
  },

  async getSecurityEventById(eventId: string): Promise<SecurityEvent> {
    return request<SecurityEvent>(`/api/v1/security/events/${eventId}`, { method: "GET" });
  },
};
