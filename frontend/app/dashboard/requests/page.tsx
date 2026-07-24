"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
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

const PAGE_SIZE = 20;

export default function RequestsPage() {
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState<Category | "">("");
  const [scenarioId, setScenarioId] = useState("");
  const [status, setStatus] = useState<AnalysisStatus | "">("");
  const [hasProblem, setHasProblem] = useState<"" | "true" | "false">("");

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

  function updateFilter(update: () => void) {
    update();
    setPage(1);
  }

  const hasActiveFilters = category || scenarioId || status || hasProblem;

  return (
    <>
      <PageHeader
        eyebrow="Журнал событий"
        title="Запросы"
        description="Формулировки пользователей, результаты классификации и статус фонового анализа."
      />

      <section className="filter-bar requests-filters" aria-label="Фильтры запросов">
        <label>
          <span>Категория</span>
          <select
            value={category}
            onChange={(event) =>
              updateFilter(() =>
                setCategory(event.target.value as Category | ""),
              )
            }
          >
            <option value="">Все категории</option>
            {CATEGORIES.map((item) => (
              <option value={item} key={item}>
                {CATEGORY_LABELS[item]}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Сценарий</span>
          <select
            value={scenarioId}
            onChange={(event) =>
              updateFilter(() => setScenarioId(event.target.value))
            }
          >
            <option value="">Все сценарии</option>
            {scenarios.data?.items.map((item) => (
              <option value={item.id} key={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Статус анализа</span>
          <select
            value={status}
            onChange={(event) =>
              updateFilter(() =>
                setStatus(event.target.value as AnalysisStatus | ""),
              )
            }
          >
            <option value="">Все статусы</option>
            {Object.entries(STATUS_LABELS).map(([value, label]) => (
              <option value={value} key={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Формулировка</span>
          <select
            value={hasProblem}
            onChange={(event) =>
              updateFilter(() =>
                setHasProblem(event.target.value as "" | "true" | "false"),
              )
            }
          >
            <option value="">Все запросы</option>
            <option value="true">Есть точки риска</option>
            <option value="false">Без точек риска</option>
          </select>
        </label>
        {hasActiveFilters ? (
          <button
            type="button"
            className="text-button"
            onClick={() => {
              setCategory("");
              setScenarioId("");
              setStatus("");
              setHasProblem("");
              setPage(1);
            }}
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
            <span className="count-label">{events.data.total} событий</span>
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
            <div className="table-scroll">
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
              onPageChange={setPage}
            />
          </>
        )}
      </section>
    </>
  );
}
