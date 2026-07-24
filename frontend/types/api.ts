export type AnalysisStatus =
  | "pending"
  | "processing"
  | "completed"
  | "failed";

export type Category =
  | "text_generation"
  | "information_search"
  | "summarization"
  | "data_analysis"
  | "reporting_export"
  | "task_management"
  | "monitoring_automation"
  | "calendar_planning"
  | "knowledge_explanation"
  | "other";

export type AutomationPotential = "low" | "medium" | "high";

export type QueryProblemReason =
  | "ambiguous"
  | "missing_context"
  | "multiple_intents"
  | "oversized_context"
  | "unsupported_task"
  | "low_classification_confidence"
  | "unclassified";

export type ImportStatus =
  | "pending"
  | "processing"
  | "completed"
  | "failed";

export interface ScenarioReference {
  id: string;
  name: string;
}

export interface EventListItem {
  id: string;
  external_id: string;
  agent_id: string;
  occurred_at: string | null;
  received_at: string;
  effective_user_query: string | null;
  category: Category | null;
  scenario: ScenarioReference | null;
  classification_confidence: number | null;
  query_problem_reasons: QueryProblemReason[] | null;
  automation_potential: AutomationPotential | null;
  analysis_status: AnalysisStatus;
}

export interface EventListResponse {
  items: EventListItem[];
  page: number;
  page_size: number;
  total: number;
}

export interface EventDetail extends EventListItem {
  model: string | null;
  stream: boolean;
  execution_status: "success" | "error" | "unknown";
  latency_ms: number | null;
  rating: number | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  warnings: string[];
}

export interface DashboardSummary {
  total_requests: number;
  analyzed_requests: number;
  pending_requests: number;
  failed_requests: number;
  category_count: number;
  scenario_count: number;
  unclassified_count: number;
  query_problem_rate: number;
}

export interface CategoryItem {
  category: Category;
  request_count: number;
  percentage: number;
}

export interface CategoryListResponse {
  items: CategoryItem[];
}

export interface ScenarioListItem {
  id: string;
  category: Category;
  name: string;
  summary: string;
  request_count: number;
  automation_potential: AutomationPotential;
  common_problems: string[];
  suggested_action: string;
}

export interface ScenarioListResponse {
  items: ScenarioListItem[];
  page: number;
  page_size: number;
  total: number;
}

export interface ScenarioDetail extends ScenarioListItem {
  representative_queries: string[];
}

export interface TimelineItem {
  date: string;
  request_count: number;
  query_problem_count: number;
}

export interface TimelineResponse {
  items: TimelineItem[];
}

export interface ImportAccepted {
  id: string;
  status: ImportStatus;
}

export interface ImportStatusResponse {
  id: string;
  filename: string;
  status: ImportStatus;
  total_rows: number;
  processed_rows: number;
  failed_rows: number;
  errors: unknown[];
}

export interface EventListParams {
  page?: number;
  page_size?: number;
  category?: Category;
  scenario_id?: string;
  analysis_status?: AnalysisStatus;
  has_query_problem?: boolean;
}

export interface ScenarioListParams {
  category?: Category;
  page?: number;
  page_size?: number;
}
