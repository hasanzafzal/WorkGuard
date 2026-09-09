export type StatusType = "Active" | "Away" | "Inactive";
export type SeverityType = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export interface Employee {
  employee_id: string;
  employee_name: string;
  sessions_count: number;
  total_active_time_seconds: number;
  last_activity: string;
  status: StatusType;
  security_alert_count: number;
}

export interface EmployeeDetail extends Employee {
  applications_used: Record<string, number>;
  session_history: Session[];
  security_events: SecurityEvent[];
  ai_observations?: string[];
  ai_confidence?: number;
  evidence_sessions?: string[];
}

export interface Session {
  session_id: string;
  employee_id: string;
  employee_name: string;
  start_time: string;
  end_time: string;
  duration_seconds: number;
  events_count: number;
  productivity_assessment?: string;
  risk_score?: number;
  security_alerts?: string[];
}

export interface SessionEvent {
  timestamp: string;
  app_name: string;
  window_title?: string;
  event_type: "focused" | "unfocused" | "process" | "file_system" | "system";
  active_seconds?: number;
  details?: string;
}

export interface SessionDetail extends Session {
  focus_summary: Record<string, number>;
  events: SessionEvent[];
  raw_payload?: Record<string, any>;
  metadata?: {
    schema_version?: string;
    created_at?: string;
    device?: string;
    os?: string;
  };
  ai_analysis?: {
    summary?: string;
    productivity_assessment?: string;
    key_activities?: string[];
    focus_observations?: string[];
    recommended_follow_up?: string[];
  };
  security_analysis?: {
    risk_score?: number;
    alerts?: string[];
    assessment?: string;
  };
}

export interface SecurityEvent {
  event_id: string;
  severity: SeverityType;
  employee_id: string;
  employee_name: string;
  detection_type: string;
  timestamp: string;
  evidence: string;
  related_session_id: string;
  ai_analysis?: string;
  recommended_action?: string;
}

export interface AIReport {
  report_id: string;
  session_id: string;
  employee_id: string;
  employee_name: string;
  date: string;
  overall_assessment: string;
  key_observations: string[];
  ai_confidence: number;
  evidence_sessions: string[];
  raw_observed_data: {
    total_duration_seconds: number;
    event_count: number;
    top_apps: string[];
  };
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  sources?: string[];
  routed_agent?: string;
  suggested_followups?: string[];
}


export interface AppUsageStat {
  app_name: string;
  active_seconds: number;
  percentage: number;
}

export interface DashboardData {
  kpis: {
    total_employees: number;
    active_employees: number;
    total_sessions: number;
    total_active_time_seconds: number;
    security_alerts: number;
  };
  workforce: Employee[];
  application_usage: AppUsageStat[];
  recent_sessions: Session[];
  security_alerts: SecurityEvent[];
  ai_overview?: {
    summary: string;
    confidence: number;
    key_highlights: string[];
  };
}
