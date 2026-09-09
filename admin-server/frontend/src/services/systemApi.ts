import { request } from "./api";

export interface ProcessingStats {
  pending: number;
  processing: number;
  completed: number;
  failed: number;
  total_documents_generated: number;
}

export interface ProcessingJob {
  session_id: string;
  status: string;
  documents_count: number;
  error_message: string | null;
  processed_at: string | null;
}

export interface ProcessingStatusResponse {
  stats: ProcessingStats;
  recent_jobs: ProcessingJob[];
}

export interface VectorStatsResponse {
  faiss_total_vectors: number;
  faiss_dimension: number;
  pg_vector_metadata_count: number;
  indexed_sessions_count: number;
  vectors_by_doc_type: Record<string, number>;
}

export interface LlmHealthResponse {
  status: string;
  base_url: string;
  configured_model: string;
  model_present: boolean;
  available_models: string[];
}

export const systemApi = {
  async getProcessingStatus(): Promise<ProcessingStatusResponse> {
    return request<ProcessingStatusResponse>("/api/v1/processing/status", {
      method: "GET",
    });
  },

  async getVectorStats(): Promise<VectorStatsResponse> {
    return request<VectorStatsResponse>("/api/v1/vectors/stats", {
      method: "GET",
    });
  },

  async getLlmHealth(): Promise<LlmHealthResponse> {
    return request<LlmHealthResponse>("/api/v1/llm/health", {
      method: "GET",
    });
  },
};
