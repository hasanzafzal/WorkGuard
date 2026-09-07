import { request } from "./api";

export interface ChatHistoryItem {
  role: string;
  content: string;
}

export interface ChatResponse {
  answer: string;
  sources: string[];
  routed_agent?: string;
  routing_reason?: string;
  employee_id?: string;
  employee_name?: string;
  suggested_followups?: string[];
  source?: string;
}

export interface ChatSuggestionsResponse {
  suggestions: string[];
  registered_employees: string[];
}

export interface ChatStatusResponse {
  status: string;
  api_layer: string;
  supervisor: string;
  agents: Record<string, string>;
  llm: Record<string, any>;
  database: Record<string, any>;
}

export const chatApi = {
  async sendMessage(
    message: string,
    conversationHistory?: ChatHistoryItem[]
  ): Promise<ChatResponse> {
    const data: any = await request("/api/v1/chat", {
      method: "POST",
      body: JSON.stringify({
        message,
        conversation_history: conversationHistory || [],
      }),
    });

    return {
      answer: data.answer || data.response || "No response received from AI agent.",
      sources: data.sources || data.citations || [],
      routed_agent: data.routed_agent,
      routing_reason: data.routing_reason,
      employee_id: data.employee_id,
      employee_name: data.employee_name,
      suggested_followups: data.suggested_followups || [],
      source: data.source,
    };
  },

  async getSuggestions(): Promise<ChatSuggestionsResponse> {
    return request("/api/v1/chat/suggestions");
  },

  async getStatus(): Promise<ChatStatusResponse> {
    return request("/api/v1/chat/status");
  },
};

