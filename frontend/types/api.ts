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
  | "code_assistance"
  | "reporting_export"
  | "task_management"
  | "monitoring_automation"
  | "calendar_planning"
  | "knowledge_explanation"
  | "non_work_general"
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
  user_id?: string | null;
  team?: string | null;
  direction?: string | null;
  is_synthetic?: boolean;
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
  task_completed: boolean | null;
  estimated_minutes_saved: number | null;
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
  response_count: number;
  rated_count: number;
  timestamped_count: number;
  dimensioned_count: number;
  synthetic_requests: number;
  value_observation_count: number;
  completed_task_count: number;
  estimated_hours_saved: number;
}

export interface CategoryItem {
  category: Category;
  request_count: number;
  percentage: number;
}

export interface CategoryListResponse {
  items: CategoryItem[];
}

export interface CategorySummaryItem {
  category: Category;
  request_count: number;
  percentage: number;
  purpose: string;
  summary: string;
  top_scenarios: string[];
  representative_queries: string[];
  top_problems: string[];
}

export interface CategorySummaryResponse {
  items: CategorySummaryItem[];
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

export interface ProblemItem {
  code: string;
  label: string;
  count: number;
  percentage: number;
  kind: "query" | "agent";
}

export interface ProblemListResponse {
  items: ProblemItem[];
  total_requests: number;
  agent_quality_available: boolean;
}

export type ScenarioTrend = "growing" | "stable" | "declining" | "new";

export interface ScenarioTrendItem {
  id: string;
  name: string;
  category: Category;
  current_count: number;
  previous_count: number;
  growth_percent: number | null;
  trend: ScenarioTrend;
}

export interface ScenarioTrendResponse {
  available: boolean;
  window_days: number;
  date_from: string | null;
  date_to: string | null;
  items: ScenarioTrendItem[];
}

export type EffectivenessDimension = "agent_id" | "team" | "direction";

export interface EffectivenessItem {
  name: string;
  total_requests: number;
  analyzed_requests: number;
  problem_rate: number;
  success_rate: number | null;
  answer_coverage: number;
  average_rating: number | null;
  average_latency_ms: number | null;
  unique_users: number | null;
  task_completion_rate: number | null;
  value_evidence_coverage: number;
  estimated_hours_saved: number;
}

export interface EffectivenessResponse {
  dimension: EffectivenessDimension;
  available: boolean;
  coverage_percent: number;
  items: EffectivenessItem[];
}

export interface DecisionRecommendation {
  kind: "automation" | "agent" | "training";
  priority: "high" | "medium" | "low";
  title: string;
  evidence: string;
  action: string;
  scope: string;
  affected_requests: number;
  examples: string[];
}

export interface DecisionSupportResponse {
  items: DecisionRecommendation[];
  data_limitations: string[];
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
