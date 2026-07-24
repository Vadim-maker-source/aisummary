from enum import StrEnum


class Category(StrEnum):
    TEXT_GENERATION = "text_generation"
    INFORMATION_SEARCH = "information_search"
    SUMMARIZATION = "summarization"
    DATA_ANALYSIS = "data_analysis"
    CODE_ASSISTANCE = "code_assistance"
    REPORTING_EXPORT = "reporting_export"
    TASK_MANAGEMENT = "task_management"
    MONITORING_AUTOMATION = "monitoring_automation"
    CALENDAR_PLANNING = "calendar_planning"
    KNOWLEDGE_EXPLANATION = "knowledge_explanation"
    OTHER = "other"


class AnalysisStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionStatus(StrEnum):
    SUCCESS = "success"
    ERROR = "error"
    UNKNOWN = "unknown"


class AutomationPotential(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class QueryProblemReason(StrEnum):
    AMBIGUOUS = "ambiguous"
    MISSING_CONTEXT = "missing_context"
    MULTIPLE_INTENTS = "multiple_intents"
    OVERSIZED_CONTEXT = "oversized_context"
    UNSUPPORTED_TASK = "unsupported_task"
    LOW_CLASSIFICATION_CONFIDENCE = "low_classification_confidence"
    UNCLASSIFIED = "unclassified"


class AnalyticsWarning(StrEnum):
    QUERY_TRUNCATED = "query_truncated"
    LLM_UNAVAILABLE = "llm_unavailable"
    LLM_INVALID_RESPONSE = "llm_invalid_response"
    NO_USER_MESSAGE = "no_user_message"
    NO_MATCHING_SCENARIO = "no_matching_scenario"


class ImportStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisRunStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

