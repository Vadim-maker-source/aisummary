"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  Building2,
  CheckCircle2,
  CircleAlert,
  Layers3,
  MessagesSquare,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import {
  AutomationBadge,
  CategoryBadge,
  EmptyState,
  ErrorState,
  LoadingBlock,
  PageHeader,
  errorMessage,
} from "@/components/ui";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  getCategories,
  getDashboardSummary,
  getEffectiveness,
  getProblems,
  getScenarioTrends,
  getScenarios,
} from "@/lib/api";
import { CATEGORY_LABELS } from "@/lib/constants";
import type { EffectivenessDimension, ScenarioTrend } from "@/types/api";

const DIMENSION_LABELS: Record<EffectivenessDimension, string> = {
  direction: "Направления",
  team: "Команды",
  agent_id: "Агенты",
};

const TREND_LABELS: Record<ScenarioTrend, string> = {
  growing: "Растёт",
  stable: "Без изменений",
  declining: "Снижается",
  new: "Новый",
};

function formatPeriod(value: string | null): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "short",
  }).format(new Date(`${value}T00:00:00Z`));
}

export default function DashboardPage() {
  const [dimension, setDimension] =
    useState<EffectivenessDimension>("direction");
  const summary = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: getDashboardSummary,
    refetchInterval: 5_000,
  });
  const categories = useQuery({
    queryKey: ["dashboard-categories"],
    queryFn: getCategories,
  });
  const problems = useQuery({
    queryKey: ["dashboard-problems"],
    queryFn: getProblems,
  });
  const trends = useQuery({
    queryKey: ["dashboard-scenario-trends", 7],
    queryFn: () => getScenarioTrends(7),
  });
  const effectiveness = useQuery({
    queryKey: ["dashboard-effectiveness", dimension],
    queryFn: () => getEffectiveness(dimension),
  });
  const scenarios = useQuery({
    queryKey: ["dashboard-scenarios", "top"],
    queryFn: () => getScenarios({ page: 1, page_size: 5 }),
  });

  const analysisCoverage = summary.data?.total_requests
    ? Math.round(
        (summary.data.analyzed_requests / summary.data.total_requests) * 100,
      )
    : 0;
  const categoryChartData =
    categories.data?.items.map((item) => ({
      ...item,
      label: CATEGORY_LABELS[item.category],
    })) ?? [];
  const maxCategoryCount = Math.max(
    1,
    ...categoryChartData.map((item) => item.request_count),
  );

  return (
    <>
      <PageHeader
        eyebrow="Отчёт для руководителя"
        title="Аналитика запросов"
        description="Что сотрудники поручают ИИ-агентам, где возникают проблемы и какие сценарии стоит развивать."
        action={
          <Button asChild>
            <Link href="/imports">Импортировать данные</Link>
          </Button>
        }
      />

      {summary.isPending ? (
        <div className="overview-metrics" aria-label="Загрузка показателей">
          {Array.from({ length: 4 }).map((_, index) => (
            <Card key={index}>
              <CardContent>
                <LoadingBlock rows={2} />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : summary.isError ? (
        <ErrorState
          message={errorMessage(summary.error)}
          onRetry={() => summary.refetch()}
        />
      ) : (
        <>
          <section className="overview-metrics" aria-label="Ключевые показатели">
            <Card className="metric-card">
              <CardHeader>
                <div className="metric-icon" aria-hidden="true">
                  <MessagesSquare size={20} />
                </div>
                <CardDescription>Запросов в выборке</CardDescription>
              </CardHeader>
              <CardContent>
                <strong className="metric-value">
                  {summary.data.total_requests.toLocaleString("ru-RU")}
                </strong>
                <p className="metric-caption">
                  {summary.data.category_count} категорий задач
                </p>
              </CardContent>
            </Card>

            <Card className="metric-card">
              <CardHeader>
                <div className="metric-icon success" aria-hidden="true">
                  <CheckCircle2 size={20} />
                </div>
                <CardDescription>Обработано</CardDescription>
              </CardHeader>
              <CardContent>
                <strong className="metric-value">{analysisCoverage}%</strong>
                <p className="metric-caption">
                  {summary.data.analyzed_requests.toLocaleString("ru-RU")} запросов
                </p>
              </CardContent>
            </Card>

            <Card className="metric-card">
              <CardHeader>
                <div className="metric-icon warning" aria-hidden="true">
                  <CircleAlert size={20} />
                </div>
                <CardDescription>Требуют внимания</CardDescription>
              </CardHeader>
              <CardContent>
                <strong className="metric-value">
                  {summary.data.query_problem_rate.toLocaleString("ru-RU")}%
                </strong>
                <p className="metric-caption">запросов с проблемами</p>
              </CardContent>
            </Card>

            <Card className="metric-card">
              <CardHeader>
                <div className="metric-icon" aria-hidden="true">
                  <Layers3 size={20} />
                </div>
                <CardDescription>Сценариев найдено</CardDescription>
              </CardHeader>
              <CardContent>
                <strong className="metric-value">
                  {summary.data.scenario_count.toLocaleString("ru-RU")}
                </strong>
                <p className="metric-caption">устойчивых способов использования</p>
              </CardContent>
            </Card>
          </section>

          <div className="sample-status" aria-label="Состояние выборки">
            <span>Состояние выборки</span>
            {summary.data.synthetic_requests > 0 ? (
              <Badge variant="warning">
                Синтетические: {summary.data.synthetic_requests}
              </Badge>
            ) : null}
            <Badge variant="outline">
              Ожидают: {summary.data.pending_requests}
            </Badge>
            <Badge
              variant={summary.data.failed_requests ? "destructive" : "outline"}
            >
              Ошибки анализа: {summary.data.failed_requests}
            </Badge>
            <Badge
              variant={
                summary.data.unclassified_count ? "warning" : "outline"
              }
            >
              Без категории: {summary.data.unclassified_count}
            </Badge>
            <Badge variant="outline">
              Ответы агента: {summary.data.response_count}
            </Badge>
          </div>
        </>
      )}

      <section className="overview-grid" aria-label="Категории и проблемы">
        <Card>
          <CardHeader className="section-card-header">
            <div>
              <CardTitle>Что чаще всего спрашивают</CardTitle>
              <CardDescription>
                Распределение задач по категориям
              </CardDescription>
            </div>
            <Button variant="ghost" size="sm" asChild>
              <Link href="/dashboard/requests">
                Все запросы <ArrowRight size={16} />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            {categories.isPending ? (
              <LoadingBlock rows={7} />
            ) : categories.isError ? (
              <ErrorState
                message={errorMessage(categories.error)}
                onRetry={() => categories.refetch()}
              />
            ) : categoryChartData.length === 0 ? (
              <EmptyState
                title="Категорий пока нет"
                description="Распределение появится после анализа загруженных запросов."
                href="/imports"
                actionLabel="Перейти к импорту"
              />
            ) : (
              <div className="category-list">
                {categoryChartData.map((item) => (
                  <div className="category-row" key={item.category}>
                    <div className="category-row-heading">
                      <span>{item.label}</span>
                      <strong>
                        {item.request_count.toLocaleString("ru-RU")}
                        <small>{item.percentage.toLocaleString("ru-RU")}%</small>
                      </strong>
                    </div>
                    <Progress
                      value={(item.request_count / maxCategoryCount) * 100}
                      aria-label={`${item.label}: ${item.request_count} запросов`}
                    />
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Топ проблем</CardTitle>
            <CardDescription>
              Что мешает запросам и ответам быть полезными
            </CardDescription>
          </CardHeader>
          <CardContent>
            {problems.isPending ? (
              <LoadingBlock rows={6} />
            ) : problems.isError ? (
              <ErrorState
                message={errorMessage(problems.error)}
                onRetry={() => problems.refetch()}
              />
            ) : problems.data.items.length === 0 ? (
              <EmptyState
                title="Проблемы не обнаружены"
                description="Для оценки ответов также нужны response, execution_status или rating."
              />
            ) : (
              <>
                <div className="problem-list">
                  {problems.data.items.slice(0, 6).map((item) => (
                    <div className="problem-row" key={item.code}>
                      <div>
                        <strong>{item.label}</strong>
                        <Badge
                          variant={item.kind === "agent" ? "warning" : "outline"}
                        >
                          {item.kind === "agent" ? "Ответ агента" : "Запрос"}
                        </Badge>
                      </div>
                      <span>
                        {item.count}
                        <small>{item.percentage}%</small>
                      </span>
                    </div>
                  ))}
                </div>
                {!problems.data.agent_quality_available ? (
                  <p className="data-notice">
                    Качество ответов не рассчитано: во входных данных нет ответов,
                    статусов выполнения или оценок.
                  </p>
                ) : null}
              </>
            )}
          </CardContent>
        </Card>
      </section>

      <section className="insight-grid" aria-label="Динамика и эффективность">
        <Card>
          <CardHeader>
            <CardTitle>Растущие сценарии</CardTitle>
            <CardDescription>
              Последние 7 дней относительно предыдущих 7 дней
            </CardDescription>
          </CardHeader>
          <CardContent>
            {trends.isPending ? (
              <LoadingBlock rows={5} />
            ) : trends.isError ? (
              <ErrorState
                message={errorMessage(trends.error)}
                onRetry={() => trends.refetch()}
              />
            ) : !trends.data.available ? (
              <EmptyState
                title="Недостаточно истории"
                description="Для сравнения нужны реальные даты минимум за два полных периода."
              />
            ) : (
              <>
                <p className="period-caption">
                  {formatPeriod(trends.data.date_from)} —{" "}
                  {formatPeriod(trends.data.date_to)}
                </p>
                <div className="trend-list">
                  {trends.data.items.slice(0, 5).map((item) => (
                    <Link
                      className="trend-row"
                      href={`/dashboard/scenarios/${item.id}`}
                      key={item.id}
                    >
                      <div>
                        <strong>{item.name}</strong>
                        <span>{CATEGORY_LABELS[item.category]}</span>
                      </div>
                      <Badge
                        variant={
                          item.trend === "declining" ? "outline" : "secondary"
                        }
                      >
                        {item.trend === "declining" ? (
                          <TrendingDown size={14} />
                        ) : (
                          <TrendingUp size={14} />
                        )}
                        {item.growth_percent === null
                          ? TREND_LABELS[item.trend]
                          : `${item.growth_percent > 0 ? "+" : ""}${item.growth_percent}%`}
                      </Badge>
                    </Link>
                  ))}
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="effectiveness-header">
            <div>
              <CardTitle>Эффективность внедрения</CardTitle>
              <CardDescription>
                Использование и качество по бизнес-разрезам
              </CardDescription>
            </div>
            <Building2 size={20} aria-hidden="true" />
          </CardHeader>
          <CardContent>
            <div className="dimension-switch" aria-label="Разрез эффективности">
              {(Object.keys(DIMENSION_LABELS) as EffectivenessDimension[]).map(
                (item) => (
                  <button
                    className={item === dimension ? "active" : ""}
                    type="button"
                    onClick={() => setDimension(item)}
                    key={item}
                  >
                    {DIMENSION_LABELS[item]}
                  </button>
                ),
              )}
            </div>
            {effectiveness.isPending ? (
              <LoadingBlock rows={5} />
            ) : effectiveness.isError ? (
              <ErrorState
                message={errorMessage(effectiveness.error)}
                onRetry={() => effectiveness.refetch()}
              />
            ) : !effectiveness.data.available ? (
              <EmptyState
                title={`Нет данных: ${DIMENSION_LABELS[dimension].toLowerCase()}`}
                description="Передавайте team, direction и user_id во входном событии. Для оценки полезности также нужны ответы, статусы или rating."
              />
            ) : (
              <>
                <p className="period-caption">
                  Заполненность разреза: {effectiveness.data.coverage_percent}%
                </p>
                <div className="effectiveness-list">
                  {effectiveness.data.items.slice(0, 5).map((item) => (
                    <div className="effectiveness-row" key={item.name}>
                      <div>
                        <strong>{item.name}</strong>
                        <span>{item.total_requests} запросов</span>
                      </div>
                      <div>
                        <strong>{item.problem_rate}%</strong>
                        <span>с проблемами</span>
                      </div>
                      <div>
                        <strong>
                          {item.success_rate === null
                            ? "—"
                            : `${item.success_rate}%`}
                        </strong>
                        <span>успешных</span>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </section>

      <Card className="scenarios-section">
        <CardHeader className="section-card-header">
          <div>
            <CardTitle>Частые сценарии и следующие действия</CardTitle>
            <CardDescription>
              Пять наиболее распространённых групп запросов
            </CardDescription>
          </div>
          <Button variant="ghost" size="sm" asChild>
            <Link href="/dashboard/scenarios">
              Все сценарии <ArrowRight size={16} />
            </Link>
          </Button>
        </CardHeader>
        <CardContent>
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
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Сценарий</TableHead>
                  <TableHead>Категория</TableHead>
                  <TableHead className="align-right">Запросов</TableHead>
                  <TableHead>Автоматизация</TableHead>
                  <TableHead className="table-action" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {scenarios.data.items.map((scenario) => (
                  <TableRow key={scenario.id}>
                    <TableCell>
                      <Link
                        className="scenario-name"
                        href={`/dashboard/scenarios/${scenario.id}`}
                      >
                        {scenario.name}
                      </Link>
                      <span className="scenario-summary">{scenario.summary}</span>
                      <span className="scenario-action-hint">
                        Действие: {scenario.suggested_action}
                      </span>
                    </TableCell>
                    <TableCell>
                      <CategoryBadge value={scenario.category} />
                    </TableCell>
                    <TableCell className="align-right numeric">
                      {scenario.request_count.toLocaleString("ru-RU")}
                    </TableCell>
                    <TableCell>
                      <AutomationBadge value={scenario.automation_potential} />
                    </TableCell>
                    <TableCell className="table-action">
                      <Button variant="ghost" size="icon" asChild>
                        <Link
                          href={`/dashboard/scenarios/${scenario.id}`}
                          aria-label={`Открыть сценарий «${scenario.name}»`}
                        >
                          <ArrowRight size={17} />
                        </Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </>
  );
}
