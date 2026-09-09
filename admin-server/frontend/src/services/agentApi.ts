import { request } from "./api";

export interface AgentQueryRequest {
  query: string;
  employee_id?: string;
  session_id?: string;
  date?: string;
}

export interface AgentResponse {
  answer: string;
  employee_id?: string;
  employee_name?: string;
  sources?: string[];
  routed_agent?: string;
  routing_reason?: string;
  confidence?: number;
  risk_score?: number;
  risk_level?: string;
  total_findings?: number;
  scope?: string;
  suggested_followups?: string[];
  metrics?: any;
}

export const agentApi = {
  async querySessionAgent(body: AgentQueryRequest): Promise<AgentResponse> {
    return request<AgentResponse>("/api/v1/agents/session-analysis", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async querySecurityAgent(body: AgentQueryRequest): Promise<AgentResponse> {
    return request<AgentResponse>("/api/v1/agents/security", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async queryReportingAgent(body: AgentQueryRequest): Promise<AgentResponse> {
    return request<AgentResponse>("/api/v1/agents/reporting", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async querySupervisorAgent(body: AgentQueryRequest): Promise<AgentResponse> {
    return request<AgentResponse>("/api/v1/agents/supervisor", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
};
