import {
  getMockImportStatus,
  getMockScenario,
  mockCategories,
  mockDashboardSummary,
  mockEvents,
  mockImportAccepted,
  mockScenarios,
  mockTimeline,
} from "@/lib/mock-data";
import type {
  CategoryListResponse,
  CategorySummaryResponse,
  DashboardSummary,
  DecisionSupportResponse,
  EffectivenessDimension,
  EffectivenessResponse,
  EventListParams,
  EventListResponse,
  ImportAccepted,
  ImportStatusResponse,
  ProblemListResponse,
  ScenarioDetail,
  ScenarioListParams,
  ScenarioListResponse,
  ScenarioTrendResponse,
  TimelineResponse,
} from "@/types/api";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";
const USE_MOCK_DATA = process.env.NEXT_PUBLIC_USE_MOCK_DATA === "true";
const MOCK_EMPTY = process.env.NEXT_PUBLIC_MOCK_EMPTY === "true";
const MOCK_ERROR = process.env.NEXT_PUBLIC_MOCK_ERROR === "true";

let mockImportFilename = "demo_events.jsonl";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

async function apiRequest<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      Accept: "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    let detail = `Ошибка API (${response.status})`;
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string") detail = payload.detail;
    } catch {
      // The status code still provides a useful typed error.
    }
    throw new ApiError(response.status, detail);
  }

  return (await response.json()) as T;
}

function searchParams(
  values: Record<string, string | number | boolean | undefined>,
): string {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== "") {
      params.set(key, String(value));
    }
  });
  const query = params.toString();
  return query ? `?${query}` : "";
}

function maybeMockError(): void {
  if (MOCK_ERROR) {
    throw new ApiError(503, "Тестовая ошибка mock API");
  }
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  if (USE_MOCK_DATA) {
    maybeMockError();
    return MOCK_EMPTY
      ? {
          total_requests: 0,
          analyzed_requests: 0,
          pending_requests: 0,
          failed_requests: 0,
          category_count: 0,
          scenario_count: 0,
          unclassified_count: 0,
          query_problem_rate: 0,
          response_count: 0,
          rated_count: 0,
          timestamped_count: 0,
          dimensioned_count: 0,
          synthetic_requests: 0,
          value_observation_count: 0,
          completed_task_count: 0,
          estimated_hours_saved: 0,
        }
      : mockDashboardSummary;
  }
  return apiRequest("/api/v1/dashboard/summary");
}

export async function getCategories(): Promise<CategoryListResponse> {
  if (USE_MOCK_DATA) {
    maybeMockError();
    return MOCK_EMPTY ? { items: [] } : mockCategories;
  }
  return apiRequest("/api/v1/dashboard/categories");
}

export async function getCategorySummaries(): Promise<CategorySummaryResponse> {
  if (USE_MOCK_DATA) {
    maybeMockError();
    return { items: [] };
  }
  return apiRequest("/api/v1/dashboard/category-summaries");
}

export async function getDecisionSupport(): Promise<DecisionSupportResponse> {
  if (USE_MOCK_DATA) {
    maybeMockError();
    return { items: [], data_limitations: [] };
  }
  return apiRequest("/api/v1/dashboard/decision-support");
}

export async function getTimeline(): Promise<TimelineResponse> {
  if (USE_MOCK_DATA) {
    maybeMockError();
    return MOCK_EMPTY ? { items: [] } : mockTimeline;
  }
  return apiRequest("/api/v1/dashboard/timeline");
}

export async function getProblems(): Promise<ProblemListResponse> {
  if (USE_MOCK_DATA) {
    maybeMockError();
    return { items: [], total_requests: 0, agent_quality_available: false };
  }
  return apiRequest("/api/v1/dashboard/problems");
}

export async function getScenarioTrends(
  windowDays = 7,
): Promise<ScenarioTrendResponse> {
  if (USE_MOCK_DATA) {
    maybeMockError();
    return {
      available: false,
      window_days: windowDays,
      date_from: null,
      date_to: null,
      items: [],
    };
  }
  return apiRequest(
    `/api/v1/dashboard/scenario-trends${searchParams({
      window_days: windowDays,
    })}`,
  );
}

export async function getEffectiveness(
  dimension: EffectivenessDimension,
): Promise<EffectivenessResponse> {
  if (USE_MOCK_DATA) {
    maybeMockError();
    return {
      dimension,
      available: false,
      coverage_percent: 0,
      items: [],
    };
  }
  return apiRequest(
    `/api/v1/dashboard/effectiveness${searchParams({ dimension })}`,
  );
}

export async function getScenarios(
  params: ScenarioListParams = {},
): Promise<ScenarioListResponse> {
  if (USE_MOCK_DATA) {
    maybeMockError();
    if (MOCK_EMPTY) {
      return {
        items: [],
        page: params.page ?? 1,
        page_size: params.page_size ?? 20,
        total: 0,
      };
    }
    const matching = params.category
      ? mockScenarios.items.filter((item) => item.category === params.category)
      : mockScenarios.items;
    const page = params.page ?? 1;
    const page_size = params.page_size ?? 20;
    const start = (page - 1) * page_size;
    return {
      items: matching.slice(start, start + page_size),
      page,
      page_size,
      total: matching.length,
    };
  }
  return apiRequest(
    `/api/v1/dashboard/scenarios${searchParams({
      category: params.category,
      page: params.page ?? 1,
      page_size: params.page_size ?? 20,
    })}`,
  );
}

export async function getScenario(id: string): Promise<ScenarioDetail> {
  if (USE_MOCK_DATA) {
    maybeMockError();
    const scenario = getMockScenario(id);
    if (!scenario) throw new ApiError(404, "Сценарий не найден");
    return scenario;
  }
  return apiRequest(`/api/v1/scenarios/${encodeURIComponent(id)}`);
}

export async function getEvents(
  params: EventListParams = {},
): Promise<EventListResponse> {
  if (USE_MOCK_DATA) {
    maybeMockError();
    if (MOCK_EMPTY) {
      return {
        items: [],
        page: params.page ?? 1,
        page_size: params.page_size ?? 20,
        total: 0,
      };
    }
    const matching = mockEvents.items.filter(
      (item) =>
        (!params.category || item.category === params.category) &&
        (!params.scenario_id || item.scenario?.id === params.scenario_id) &&
        (!params.analysis_status ||
          item.analysis_status === params.analysis_status) &&
        (params.has_query_problem === undefined ||
          (params.has_query_problem
            ? Boolean(item.query_problem_reasons?.length)
            : !item.query_problem_reasons?.length)),
    );
    const page = params.page ?? 1;
    const page_size = params.page_size ?? 20;
    const start = (page - 1) * page_size;
    return {
      items: matching.slice(start, start + page_size),
      page,
      page_size,
      total: matching.length,
    };
  }
  return apiRequest(
    `/api/v1/events${searchParams({
      page: params.page ?? 1,
      page_size: params.page_size ?? 20,
      category: params.category,
      scenario_id: params.scenario_id,
      analysis_status: params.analysis_status,
      has_query_problem: params.has_query_problem,
    })}`,
  );
}

export async function uploadImport(file: File): Promise<ImportAccepted> {
  if (USE_MOCK_DATA) {
    maybeMockError();
    mockImportFilename = file.name;
    return mockImportAccepted;
  }
  const formData = new FormData();
  formData.append("file", file);
  return apiRequest("/api/v1/imports", {
    method: "POST",
    body: formData,
  });
}

export async function getImportStatus(
  id: string,
): Promise<ImportStatusResponse> {
  if (USE_MOCK_DATA) {
    maybeMockError();
    return getMockImportStatus(mockImportFilename);
  }
  return apiRequest(`/api/v1/imports/${encodeURIComponent(id)}`);
}
