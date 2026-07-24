import type {
  CategoryListResponse,
  DashboardSummary,
  EventListResponse,
  ImportAccepted,
  ImportStatusResponse,
  ScenarioDetail,
  ScenarioListResponse,
  TimelineResponse,
} from "@/types/api";

export const mockDashboardSummary = {
  total_requests: 2486,
  analyzed_requests: 2389,
  pending_requests: 84,
  failed_requests: 13,
  category_count: 9,
  scenario_count: 22,
  unclassified_count: 71,
  query_problem_rate: 14.6,
} satisfies DashboardSummary;

export const mockCategories = {
  items: [
    {
      category: "calendar_planning",
      request_count: 582,
      percentage: 23.4,
    },
    {
      category: "information_search",
      request_count: 471,
      percentage: 18.9,
    },
    { category: "summarization", request_count: 406, percentage: 16.3 },
    { category: "text_generation", request_count: 352, percentage: 14.2 },
    { category: "data_analysis", request_count: 287, percentage: 11.5 },
    { category: "task_management", request_count: 192, percentage: 7.7 },
    {
      category: "reporting_export",
      request_count: 125,
      percentage: 5.0,
    },
    { category: "other", request_count: 71, percentage: 2.9 },
  ],
} satisfies CategoryListResponse;

export const mockScenarios = {
  items: [
    {
      id: "3dd46363-4bcb-473f-a01b-52ab1d9d7f41",
      category: "calendar_planning",
      name: "Подбор времени встречи",
      summary:
        "Пользователи просят найти общий свободный слот для нескольких участников.",
      request_count: 286,
      automation_potential: "high",
      common_problems: ["Не указан часовой пояс", "Неясен состав участников"],
      suggested_action:
        "Добавить специализированный календарный workflow с проверкой доступности.",
    },
    {
      id: "1f0b8314-3c3e-43ab-9baa-b1f1c8a0e702",
      category: "summarization",
      name: "Ежедневная сводка переписки",
      summary:
        "Сотрудники запрашивают краткую сводку писем и рабочих обсуждений за период.",
      request_count: 221,
      automation_potential: "high",
      common_problems: ["Не задан период"],
      suggested_action:
        "Создать ежедневную автоматическую сводку по выбранным каналам.",
    },
    {
      id: "a74c8a8d-cab8-4db0-aa6a-c56ed143b2e7",
      category: "information_search",
      name: "Поиск данных о клиенте",
      summary:
        "Запросы на сбор контактов, статуса сделок и истории взаимодействия.",
      request_count: 188,
      automation_potential: "medium",
      common_problems: ["Клиент указан не полностью"],
      suggested_action:
        "Связать поиск с CRM и добавить уточнение при совпадении имён.",
    },
    {
      id: "22222222-2222-4222-8222-222222222222",
      category: "data_analysis",
      name: "Анализ отклонений в метриках",
      summary:
        "Команды ищут причины изменений ключевых показателей в таблицах.",
      request_count: 154,
      automation_potential: "medium",
      common_problems: ["Не указана базовая линия", "Нет периода сравнения"],
      suggested_action:
        "Добавить шаблон анализа с обязательным периодом и базовой метрикой.",
    },
    {
      id: "33333333-3333-4333-8333-333333333333",
      category: "task_management",
      name: "Создание задач из переписки",
      summary:
        "Пользователи просят переносить договорённости из обсуждений в трекер.",
      request_count: 132,
      automation_potential: "high",
      common_problems: ["Не назначен исполнитель"],
      suggested_action:
        "Предлагать карточку задачи и просить подтверждение перед созданием.",
    },
    {
      id: "44444444-4444-4444-8444-444444444444",
      category: "text_generation",
      name: "Подготовка деловых писем",
      summary:
        "Запросы на черновики писем клиентам и партнёрам в заданном тоне.",
      request_count: 97,
      automation_potential: "medium",
      common_problems: ["Не указан тон сообщения"],
      suggested_action: "Добавить набор корпоративных стилевых шаблонов.",
    },
  ],
  page: 1,
  page_size: 20,
  total: 6,
} satisfies ScenarioListResponse;

export const mockTimeline = {
  items: [
    { date: "2026-07-18", request_count: 292, query_problem_count: 38 },
    { date: "2026-07-19", request_count: 318, query_problem_count: 46 },
    { date: "2026-07-20", request_count: 274, query_problem_count: 41 },
    { date: "2026-07-21", request_count: 346, query_problem_count: 54 },
    { date: "2026-07-22", request_count: 381, query_problem_count: 57 },
    { date: "2026-07-23", request_count: 419, query_problem_count: 61 },
    { date: "2026-07-24", request_count: 456, query_problem_count: 66 },
  ],
} satisfies TimelineResponse;

export const mockEvents = {
  items: [
    {
      id: "0e2b1d1c-b3bf-4889-aad8-88ea395e5e23",
      external_id: "request-123",
      agent_id: "corporate-agent",
      occurred_at: "2026-07-24T10:00:00Z",
      received_at: "2026-07-24T10:00:01Z",
      effective_user_query: "Найди общий слот для встречи команды на этой неделе",
      category: "calendar_planning",
      scenario: {
        id: "3dd46363-4bcb-473f-a01b-52ab1d9d7f41",
        name: "Подбор времени встречи",
      },
      classification_confidence: 0.93,
      query_problem_reasons: ["missing_context"],
      automation_potential: "high",
      analysis_status: "completed",
    },
    {
      id: "572408a0-1e39-4a61-b61b-7f71ddde020a",
      external_id: "request-124",
      agent_id: "sales-copilot",
      occurred_at: "2026-07-24T09:34:00Z",
      received_at: "2026-07-24T09:34:02Z",
      effective_user_query: "Собери краткую сводку писем клиента за неделю",
      category: "summarization",
      scenario: {
        id: "1f0b8314-3c3e-43ab-9baa-b1f1c8a0e702",
        name: "Ежедневная сводка переписки",
      },
      classification_confidence: 0.89,
      query_problem_reasons: [],
      automation_potential: "high",
      analysis_status: "completed",
    },
    {
      id: "66572f34-9931-4828-a561-b677062bad07",
      external_id: "request-125",
      agent_id: "data-assistant",
      occurred_at: "2026-07-24T09:18:00Z",
      received_at: "2026-07-24T09:18:03Z",
      effective_user_query: "Почему конверсия изменилась?",
      category: "data_analysis",
      scenario: {
        id: "22222222-2222-4222-8222-222222222222",
        name: "Анализ отклонений в метриках",
      },
      classification_confidence: 0.71,
      query_problem_reasons: ["missing_context", "ambiguous"],
      automation_potential: "medium",
      analysis_status: "completed",
    },
    {
      id: "737fdb83-9c71-47a8-a115-bd86b7a11bd4",
      external_id: "request-126",
      agent_id: "corporate-agent",
      occurred_at: "2026-07-24T09:02:00Z",
      received_at: "2026-07-24T09:02:01Z",
      effective_user_query: null,
      category: null,
      scenario: null,
      classification_confidence: null,
      query_problem_reasons: null,
      automation_potential: null,
      analysis_status: "pending",
    },
    {
      id: "4c5e7ac8-f1ee-4dc2-85a6-8dc878d401d2",
      external_id: "request-127",
      agent_id: "support-agent",
      occurred_at: null,
      received_at: "2026-07-24T08:50:01Z",
      effective_user_query: "Разбери обращение и создай задачу",
      category: null,
      scenario: null,
      classification_confidence: null,
      query_problem_reasons: null,
      automation_potential: null,
      analysis_status: "processing",
    },
  ],
  page: 1,
  page_size: 20,
  total: 5,
} satisfies EventListResponse;

export function getMockScenario(id: string): ScenarioDetail | undefined {
  const scenario = mockScenarios.items.find((item) => item.id === id);
  if (!scenario) return undefined;

  const queries: Record<string, string[]> = {
    "3dd46363-4bcb-473f-a01b-52ab1d9d7f41": [
      "Найди время, когда все свободны",
      "Подбери общий слот для встречи",
      "Когда команде удобно созвониться на этой неделе?",
    ],
    "1f0b8314-3c3e-43ab-9baa-b1f1c8a0e702": [
      "Сделай краткую сводку писем за день",
      "Подготовь дайджест переписки с клиентом",
      "Что важного было в почте за неделю?",
    ],
  };

  return {
    ...scenario,
    representative_queries: queries[id] ?? [
      `Покажи типичный запрос для сценария «${scenario.name}»`,
      `Помоги выполнить сценарий «${scenario.name}»`,
    ],
  };
}

export const mockImportAccepted = {
  id: "fc1beeb0-98b1-4b8a-b29b-fe586a3e75c2",
  status: "pending",
} satisfies ImportAccepted;

export function getMockImportStatus(
  filename = "demo_events.jsonl",
): ImportStatusResponse {
  return {
    id: mockImportAccepted.id,
    filename,
    status: "completed",
    total_rows: 500,
    processed_rows: 498,
    failed_rows: 2,
    errors: [
      { row: 119, detail: "Поле agent_id обязательно" },
      { row: 407, detail: "Неверный формат occurred_at" },
    ],
  };
}
