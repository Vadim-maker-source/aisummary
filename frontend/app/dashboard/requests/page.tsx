"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import {
  AutomationBadge,
  CategoryBadge,
  EmptyState,
  ErrorState,
  LoadingBlock,
  PageHeader,
  Pagination,
  StatusBadge,
  errorMessage,
  formatCount,
  formatDate,
} from "@/components/ui";
import { getEvents, getScenarios } from "@/lib/api";
import {
  CATEGORIES,
  CATEGORY_LABELS,
  PROBLEM_LABELS,
  STATUS_LABELS,
} from "@/lib/constants";
import type { AnalysisStatus, Category } from "@/types/api";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const PAGE_SIZE = 20;
const ALL_FILTER = "__all__";

export default function RequestsPage() {
  return (
    <>
      <PageHeader
        eyebrow="Журнал событий"
        title="Запросы"
        description="Формулировки пользователей, результаты классификации и статус фонового анализа."
      />
      <Suspense
        fallback={
          <section className="panel" aria-label="Загрузка журнала запросов">
            <LoadingBlock rows={7} />
          </section>
        }
      >
        <RequestsContent />
      </Suspense>
    </>
  );
}

function readPage(value: string | null): number {
  const page = Number(value);
  return Number.isInteger(page) && page > 0 ? page : 1;
}

function RequestsContent() {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();

  const page = readPage(searchParams.get("page"));
  const categoryParam = searchParams.get("category");
  const category =
    categoryParam && CATEGORIES.includes(categoryParam as Category)
      ? (categoryParam as Category)
      : "";
  const scenarioId = searchParams.get("scenario_id") ?? "";
  const statusParam = searchParams.get("analysis_status");
  const status =
    statusParam &&
    Object.prototype.hasOwnProperty.call(STATUS_LABELS, statusParam)
      ? (statusParam as AnalysisStatus)
      : "";
  const hasProblemParam = searchParams.get("has_query_problem");
  const hasProblem =
    hasProblemParam === "true" || hasProblemParam === "false"
      ? hasProblemParam
      : "";

  const events = useQuery({
    queryKey: ["events", page, category, scenarioId, status, hasProblem],
    queryFn: () =>
      getEvents({
        page,
        page_size: PAGE_SIZE,
        category: category || undefined,
        scenario_id: scenarioId || undefined,
        analysis_status: status || undefined,
        has_query_problem:
          hasProblem === "" ? undefined : hasProblem === "true",
      }),
    refetchInterval: 5_000,
  });

  const scenarios = useQuery({
    queryKey: ["scenarios", "filter-options"],
    queryFn: () => getScenarios({ page: 1, page_size: 100 }),
  });

  function updateParams(
    updates: Record<string, string | null>,
    resetPage = false,
  ) {
    const params = new URLSearchParams(searchParams.toString());
    Object.entries(updates).forEach(([key, value]) => {
      if (value) {
        params.set(key, value);
      } else {
        params.delete(key);
      }
    });
    if (resetPage) params.delete("page");
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, {
      scroll: false,
    });
  }

  const hasActiveFilters = category || scenarioId || status || hasProblem;

  return (
    <>
      <section className="filter-bar requests-filters" aria-label="Фильтры запросов">
        <label>
          <span>Категория</span>
          <Select
            value={category || ALL_FILTER}
            onValueChange={(value) =>
              updateParams(
                { category: value === ALL_FILTER ? null : value },
                true,
              )
            }
          >
            <SelectTrigger aria-label="Категория">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL_FILTER}>Все категории</SelectItem>
              {CATEGORIES.map((item) => (
                <SelectItem value={item} key={item}>
                  {CATEGORY_LABELS[item]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </label>
        <label>
          <span>Сценарий</span>
          <Select
            value={scenarioId || ALL_FILTER}
            onValueChange={(value) =>
              updateParams(
                { scenario_id: value === ALL_FILTER ? null : value },
                true,
              )
            }
          >
            <SelectTrigger aria-label="Сценарий">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL_FILTER}>Все сценарии</SelectItem>
              {scenarios.data?.items.map((item) => (
                <SelectItem value={item.id} key={item.id}>
                  {item.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </label>
        <label>
          <span>Статус анализа</span>
          <Select
            value={status || ALL_FILTER}
            onValueChange={(value) =>
              updateParams(
                { analysis_status: value === ALL_FILTER ? null : value },
                true,
              )
            }
          >
            <SelectTrigger aria-label="Статус анализа">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL_FILTER}>Все статусы</SelectItem>
              {Object.entries(STATUS_LABELS).map(([value, label]) => (
                <SelectItem value={value} key={value}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </label>
        <label>
          <span>Формулировка</span>
          <Select
            value={hasProblem || ALL_FILTER}
            onValueChange={(value) =>
              updateParams(
                {
                  has_query_problem:
                    value === ALL_FILTER ? null : value,
                },
                true,
              )
            }
          >
            <SelectTrigger aria-label="Формулировка">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL_FILTER}>Все запросы</SelectItem>
              <SelectItem value="true">Есть точки риска</SelectItem>
              <SelectItem value="false">Без точек риска</SelectItem>
            </SelectContent>
          </Select>
        </label>
        {hasActiveFilters ? (
          <button
            type="button"
            className="text-button"
            onClick={() =>
              updateParams(
                {
                  category: null,
                  scenario_id: null,
                  analysis_status: null,
                  has_query_problem: null,
                },
                true,
              )
            }
          >
            Сбросить
          </button>
        ) : null}
      </section>

      <section className="panel" aria-labelledby="requests-list-title">
        <div className="panel-heading">
          <div>
            <p className="panel-kicker">Данные обновляются каждые 5 секунд</p>
            <h2 id="requests-list-title">Последние запросы</h2>
          </div>
          {events.data ? (
            <span className="count-label">
              {formatCount(events.data.total, [
                "событие",
                "события",
                "событий",
              ])}
            </span>
          ) : null}
        </div>

        {events.isPending ? (
          <LoadingBlock rows={7} />
        ) : events.isError ? (
          <ErrorState
            message={errorMessage(events.error)}
            onRetry={() => events.refetch()}
          />
        ) : events.data.items.length === 0 ? (
          <EmptyState
            title="Запросов не найдено"
            description={
              hasActiveFilters
                ? "Измените фильтры, чтобы увидеть больше событий."
                : "Импортируйте события, чтобы начать анализ."
            }
            href={hasActiveFilters ? undefined : "/imports"}
            actionLabel={hasActiveFilters ? undefined : "Перейти к импорту"}
          />
        ) : (
          <>
            <div className="table-scroll requests-table-scroll">
              <table className="requests-table">
                <thead>
                  <tr>
                    <th>Время</th>
                    <th>Агент</th>
                    <th>Запрос пользователя</th>
                    <th>Категория</th>
                    <th>Сценарий</th>
                    <th>Уверенность</th>
                    <th>Точки риска</th>
                    <th>Автоматизация</th>
                    <th>Статус</th>
                  </tr>
                </thead>
                <tbody>
                  {events.data.items.map((event) => (
                    <tr key={event.id}>
                      <td className="nowrap">{formatDate(event.occurred_at)}</td>
                      <td>
                        <code>{event.agent_id}</code>
                      </td>
                      <td className="query-cell">
                        {event.effective_user_query ?? "—"}
                      </td>
                      <td>
                        {event.category ? (
                          <CategoryBadge value={event.category} />
                        ) : (
                          "—"
                        )}
                      </td>
                      <td>
                        {event.scenario ? (
                          <Link
                            className="subtle-link"
                            href={`/dashboard/scenarios/${event.scenario.id}`}
                          >
                            {event.scenario.name}
                          </Link>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="numeric">
                        {event.classification_confidence === null
                          ? "—"
                          : `${Math.round(event.classification_confidence * 100)}%`}
                      </td>
                      <td>
                        {event.query_problem_reasons === null
                          ? "—"
                          : event.query_problem_reasons.length === 0
                            ? "Нет"
                            : event.query_problem_reasons
                                .map((reason) => PROBLEM_LABELS[reason])
                                .join(", ")}
                      </td>
                      <td>
                        {event.automation_potential ? (
                          <AutomationBadge value={event.automation_potential} />
                        ) : (
                          "—"
                        )}
                      </td>
                      <td>
                        <StatusBadge value={event.analysis_status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination
              page={events.data.page}
              pageSize={events.data.page_size}
              total={events.data.total}
              onPageChange={(nextPage) =>
                updateParams({
                  page: nextPage === 1 ? null : String(nextPage),
                })
              }
            />
          </>
        )}
      </section>
    </>
  );
}
