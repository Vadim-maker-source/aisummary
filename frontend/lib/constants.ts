import type {
  AnalysisStatus,
  AutomationPotential,
  Category,
  QueryProblemReason,
} from "@/types/api";

export const CATEGORIES: Category[] = [
  "text_generation",
  "information_search",
  "summarization",
  "data_analysis",
  "code_assistance",
  "reporting_export",
  "task_management",
  "monitoring_automation",
  "calendar_planning",
  "knowledge_explanation",
  "non_work_general",
  "other",
];

export const CATEGORY_LABELS: Record<Category, string> = {
  text_generation: "Генерация текста",
  information_search: "Поиск информации",
  summarization: "Саммаризация",
  data_analysis: "Анализ данных",
  code_assistance: "Помощь с кодом",
  reporting_export: "Отчёты и экспорт",
  task_management: "Управление задачами",
  monitoring_automation: "Мониторинг",
  calendar_planning: "Планирование",
  knowledge_explanation: "Объяснение знаний",
  non_work_general: "Нерабочие и общие вопросы",
  other: "Другое",
};

export const AUTOMATION_LABELS: Record<AutomationPotential, string> = {
  high: "Высокий",
  medium: "Средний",
  low: "Низкий",
};

export const STATUS_LABELS: Record<AnalysisStatus, string> = {
  pending: "Ожидает анализа",
  processing: "Анализируется",
  completed: "Проанализирован",
  failed: "Ошибка анализа",
};

export const PROBLEM_LABELS: Record<QueryProblemReason, string> = {
  ambiguous: "Неоднозначность",
  missing_context: "Недостаточно контекста",
  multiple_intents: "Несколько намерений",
  oversized_context: "Слишком большой контекст",
  unsupported_task: "Задача не поддерживается",
  low_classification_confidence: "Низкая уверенность",
  unclassified: "Не классифицировано",
};

export const IMPORT_STATUS_LABELS = {
  pending: "Ожидает обработки",
  processing: "Обрабатывается",
  completed: "Завершён",
  failed: "Ошибка",
} as const;
