import Link from "next/link";
import {
  AUTOMATION_LABELS,
  CATEGORY_LABELS,
  STATUS_LABELS,
} from "@/lib/constants";
import type {
  AnalysisStatus,
  AutomationPotential,
  Category,
} from "@/types/api";

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="page-description">{description}</p>
      </div>
      {action ? <div className="page-action">{action}</div> : null}
    </header>
  );
}

export function CategoryBadge({ value }: { value: Category }) {
  return (
    <span className={`badge category category-${value}`}>
      {CATEGORY_LABELS[value]}
    </span>
  );
}

export function AutomationBadge({
  value,
}: {
  value: AutomationPotential;
}) {
  return (
    <span className={`badge automation automation-${value}`}>
      {AUTOMATION_LABELS[value]}
    </span>
  );
}

export function StatusBadge({ value }: { value: AnalysisStatus }) {
  return (
    <span className={`badge status status-${value}`}>
      <span className="badge-dot" aria-hidden="true" />
      {STATUS_LABELS[value]}
    </span>
  );
}

export function EmptyState({
  title,
  description,
  href,
  actionLabel,
}: {
  title: string;
  description: string;
  href?: string;
  actionLabel?: string;
}) {
  return (
    <div className="empty-state">
      <div className="empty-symbol" aria-hidden="true">
        ∅
      </div>
      <h3>{title}</h3>
      <p>{description}</p>
      {href && actionLabel ? (
        <Link className="button secondary" href={href}>
          {actionLabel}
        </Link>
      ) : null}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="error-state" role="alert">
      <strong>Не удалось загрузить данные</strong>
      <p>{message}</p>
      {onRetry ? (
        <button className="button secondary" type="button" onClick={onRetry}>
          Повторить
        </button>
      ) : null}
    </div>
  );
}

export function LoadingBlock({ rows = 3 }: { rows?: number }) {
  return (
    <div className="loading-block" aria-label="Загрузка" aria-busy="true">
      {Array.from({ length: rows }).map((_, index) => (
        <span key={index} style={{ width: `${92 - index * 8}%` }} />
      ))}
    </div>
  );
}

export function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
}: {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const first = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, total);

  return (
    <div className="pagination">
      <p>
        {first}–{last} из {total}
      </p>
      <div>
        <button
          type="button"
          className="icon-button"
          aria-label="Предыдущая страница"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          ←
        </button>
        <span>
          {page} / {pages}
        </span>
        <button
          type="button"
          className="icon-button"
          aria-label="Следующая страница"
          disabled={page >= pages}
          onClick={() => onPageChange(page + 1)}
        >
          →
        </button>
      </div>
    </div>
  );
}

export function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function formatCount(
  value: number,
  forms: readonly [string, string, string],
): string {
  const absolute = Math.abs(value) % 100;
  const lastDigit = absolute % 10;
  const form =
    absolute > 10 && absolute < 20
      ? forms[2]
      : lastDigit === 1
        ? forms[0]
        : lastDigit >= 2 && lastDigit <= 4
          ? forms[1]
          : forms[2];

  return `${value.toLocaleString("ru-RU")} ${form}`;
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Неизвестная ошибка";
}
