"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  AutomationBadge,
  EmptyState,
  ErrorState,
  LoadingBlock,
  PageHeader,
  errorMessage,
} from "@/components/ui";
import {
  getCategories,
  getDashboardSummary,
  getScenarios,
  getTimeline,
} from "@/lib/api";
import { CATEGORY_LABELS } from "@/lib/constants";

const kpiConfig = [
  { field: "total_requests", label: "Всего запросов", tone: "ink" },
  { field: "analyzed_requests", label: "Проанализировано", tone: "success" },
  { field: "pending_requests", label: "Ожидают анализа", tone: "warning" },
  { field: "failed_requests", label: "Ошибки анализа", tone: "danger" },
  { field: "category_count", label: "Категории", tone: "blue" },
  { field: "scenario_count", label: "Сценарии", tone: "violet" },
  { field: "unclassified_count", label: "Не классифицировано", tone: "muted" },
  {
    field: "query_problem_rate",
    label: "Проблемные формулировки",
    tone: "risk",
    percent: true,
  },
] as const;

export default function DashboardPage() {
  const summary = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: getDashboardSummary,
    refetchInterval: 5_000,
  });
  const categories = useQuery({
    queryKey: ["dashboard-categories"],
    queryFn: getCategories,
  });
  const timeline = useQuery({
    queryKey: ["dashboard-timeline"],
    queryFn: getTimeline,
  });
  const scenarios = useQuery({
    queryKey: ["dashboard-scenarios", "top"],
    queryFn: () => getScenarios({ page: 1, page_size: 5 }),
  });

  const categoryChartData =
    categories.data?.items.map((item) => ({
      ...item,
      label: CATEGORY_LABELS[item.category],
    })) ?? [];
  const timelineData =
    timeline.data?.items.map((item) => ({
      ...item,
      label: new Intl.DateTimeFormat("ru-RU", {
        day: "2-digit",
        month: "short",
      }).format(new Date(`${item.date}T00:00:00Z`)),
    })) ?? [];
  const categoryChartDescription = categoryChartData
    .map(
      (item) =>
        `${item.label}: ${item.request_count.toLocaleString("ru-RU")} запросов, ${item.percentage.toLocaleString("ru-RU")}%`,
    )
    .join("; ");
  const largestCategoryCount = Math.max(
    ...categoryChartData.map((item) => item.request_count),
    1,
  );
  const timelineChartDescription = timelineData
    .map(
      (item) =>
        `${item.label}: ${item.request_count.toLocaleString("ru-RU")} запросов, проблемных формулировок — ${item.query_problem_count.toLocaleString("ru-RU")}`,
    )
    .join("; ");

  return (
    <>
      <PageHeader
        eyebrow="Обзор"
        title="Аналитика запросов"
        description="Категории, сценарии и сложные формулировки запросов."
        action={
          <Link className="button primary" href="/imports">
            + Импортировать данные
          </Link>
        }
      />

      <section aria-labelledby="kpi-title">
        <div className="section-heading">
          <div>
            <h2 id="kpi-title">Ключевые показатели</h2>
            <p>Обновляются автоматически каждые 5 секунд</p>
          </div>
          <span className="live-label">
            <span className="status-dot" aria-hidden="true" />
            Обновляется
          </span>
        </div>

        {summary.isPending ? (
          <div className="kpi-grid" aria-label="Загрузка показателей">
            {kpiConfig.map((item) => (
              <div className="kpi-card skeleton-card" key={item.field}>
                <LoadingBlock rows={2} />
              </div>
            ))}
          </div>
        ) : summary.isError ? (
          <ErrorState
            message={errorMessage(summary.error)}
            onRetry={() => summary.refetch()}
          />
        ) : (
          <div className="kpi-grid">
            {kpiConfig.map((item, index) => {
              const value = summary.data[item.field];
              return (
                <article className={`kpi-card tone-${item.tone}`} key={item.field}>
                  <div className="kpi-card-heading">
                    <span className="kpi-index">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <p>{item.label}</p>
                  </div>
                  <strong>
                    {value.toLocaleString("ru-RU")}
                    {"percent" in item && item.percent ? <small>%</small> : null}
                  </strong>
                </article>
              );
            })}
          </div>
        )}
      </section>

      <div className="dashboard-grid">
        <section className="panel chart-panel" aria-labelledby="categories-title">
          <div className="panel-heading">
            <div>
              <h2 id="categories-title">Запросы по категориям</h2>
            </div>
            <Link href="/dashboard/requests">Все запросы →</Link>
          </div>
          {categories.isPending ? (
            <LoadingBlock rows={5} />
          ) : categories.isError ? (
            <ErrorState
              message={errorMessage(categories.error)}
              onRetry={() => categories.refetch()}
            />
          ) : categoryChartData.length === 0 ? (
            <EmptyState
              title="Категорий пока нет"
              description="Импортируйте события — распределение появится после анализа."
              href="/imports"
              actionLabel="Перейти к импорту"
            />
          ) : (
            <>
              <p className="sr-only" id="categories-chart-description">
                {categoryChartDescription}
              </p>
              <div
                className="category-bars"
                role="img"
                aria-label="Горизонтальная диаграмма запросов по категориям"
                aria-describedby="categories-chart-description"
              >
                {categoryChartData.map((item) => (
                  <div className="category-bar-row" key={item.category}>
                    <div className="category-bar-copy">
                      <span>{item.label}</span>
                      <div>
                        <strong>{item.request_count.toLocaleString("ru-RU")}</strong>
                        <small>{item.percentage.toLocaleString("ru-RU")}%</small>
                      </div>
                    </div>
                    <div className="category-bar-track" aria-hidden="true">
                      <span
                        style={{
                          width: `${(item.request_count / largestCategoryCount) * 100}%`,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </section>

        <section className="panel chart-panel" aria-labelledby="timeline-title">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Динамика</p>
              <h2 id="timeline-title">Запросы за период</h2>
            </div>
            <div className="chart-legend" aria-label="Обозначения графика">
              <span>
                <i className="legend-total" aria-hidden="true" />
                Все запросы
              </span>
              <span>
                <i className="legend-problem" aria-hidden="true" />
                Проблемные
              </span>
            </div>
          </div>
          {timeline.isPending ? (
            <LoadingBlock rows={5} />
          ) : timeline.isError ? (
            <ErrorState
              message={errorMessage(timeline.error)}
              onRetry={() => timeline.refetch()}
            />
          ) : timelineData.length === 0 ? (
            <EmptyState
              title="Нет данных за период"
              description="События без occurred_at не включаются в timeline."
            />
          ) : (
            <>
              <p className="sr-only" id="timeline-chart-description">
                {timelineChartDescription}
              </p>
              <div
                className="chart-wrap"
                role="img"
                aria-label="Линейный график запросов и проблемных формулировок"
                aria-describedby="timeline-chart-description"
              >
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={timelineData}
                    margin={{ top: 12, right: 16, bottom: 0, left: -18 }}
                  >
                    <CartesianGrid stroke="#e7e8e2" vertical={false} />
                    <XAxis
                      dataKey="label"
                      tick={{ fill: "#737982", fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fill: "#737982", fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "#ffffff",
                        border: 0,
                        borderRadius: 10,
                        boxShadow: "0 10px 28px rgba(20, 25, 35, 0.12)",
                        fontSize: 11,
                      }}
                    />
                    <Line
                      type="linear"
                      dataKey="request_count"
                      name="Все запросы"
                      stroke="#2457f5"
                      strokeWidth={2.5}
                      dot={{ r: 2.5, fill: "#2457f5", strokeWidth: 0 }}
                      activeDot={{ r: 4, strokeWidth: 0 }}
                    />
                    <Line
                      type="linear"
                      dataKey="query_problem_count"
                      name="Проблемные"
                      stroke="#8c6b00"
                      strokeWidth={2}
                      dot={{ r: 2, fill: "#8c6b00", strokeWidth: 0 }}
                      activeDot={{ r: 3.5, strokeWidth: 0 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </>
          )}
        </section>
      </div>

      <section className="panel" aria-labelledby="top-scenarios-title">
        <div className="panel-heading">
          <div>
            <p className="panel-kicker">Сценарии для автоматизации</p>
            <h2 id="top-scenarios-title">Топ сценариев</h2>
          </div>
          <Link href="/dashboard/scenarios">Все сценарии →</Link>
        </div>
        {scenarios.isPending ? (
          <LoadingBlock rows={5} />
        ) : scenarios.isError ? (
          <ErrorState
            message={errorMessage(scenarios.error)}
            onRetry={() => scenarios.refetch()}
          />
        ) : scenarios.data.items.length === 0 ? (
          <EmptyState
            title="Сценарии ещё не обнаружены"
            description="Они появятся после анализа и группировки похожих запросов."
          />
        ) : (
          <div className="table-scroll">
            <table className="top-scenarios-table">
              <thead>
                <tr>
                  <th>Сценарий</th>
                  <th>Категория</th>
                  <th className="align-center">Запросы</th>
                  <th>Автоматизация</th>
                  <th aria-label="Открыть" />
                </tr>
              </thead>
              <tbody>
                {scenarios.data.items.slice(0, 5).map((scenario) => (
                  <tr key={scenario.id}>
                    <td>
                      <Link
                        className="table-primary-link"
                        href={`/dashboard/scenarios/${scenario.id}`}
                      >
                        {scenario.name}
                      </Link>
                      <small className="cell-subtitle">{scenario.summary}</small>
                    </td>
                    <td>{CATEGORY_LABELS[scenario.category]}</td>
                    <td className="align-center numeric">
                      {scenario.request_count}
                    </td>
                    <td>
                      <AutomationBadge value={scenario.automation_potential} />
                    </td>
                    <td>
                      <Link
                        className="row-arrow"
                        href={`/dashboard/scenarios/${scenario.id}`}
                        aria-label={`Открыть сценарий «${scenario.name}»`}
                      >
                        →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
