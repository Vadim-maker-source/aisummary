"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  Building2,
  CheckCircle2,
  CircleAlert,
  Clock3,
  Download,
  GraduationCap,
  Layers3,
  MessagesSquare,
  Sparkles,
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
  getCategorySummaries,
  getDashboardSummary,
  getDecisionSupport,
  downloadDashboardReport,
  getEffectiveness,
  getProblems,
  getScenarioTrends,
  getScenarios,
} from "@/lib/api";
import { CATEGORY_LABELS } from "@/lib/constants";
import type {
  EffectivenessDimension,
  ReportFormat,
  ScenarioTrend,
} from "@/types/api";

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
  const [reportFormat, setReportFormat] = useState<ReportFormat>("pdf");
  const reportExport = useMutation({
    mutationFn: () => downloadDashboardReport(reportFormat),
    onSuccess: ({ blob, filename }) => {
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    },
  });
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
  const categorySummaries = useQuery({
    queryKey: ["dashboard-category-summaries"],
    queryFn: getCategorySummaries,
  });
  const decisionSupport = useQuery({
    queryKey: ["dashboard-decision-support"],
    queryFn: getDecisionSupport,
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
          <div className="report-page-actions">
            <div className="report-export-control">
              <Select
                value={reportFormat}
                onValueChange={(value) =>
                  setReportFormat(value as ReportFormat)
                }
              >
                <SelectTrigger aria-label="Формат отчёта">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pdf">PDF</SelectItem>
                  <SelectItem value="md">Markdown (.md)</SelectItem>
                  <SelectItem value="csv">CSV</SelectItem>
                  <SelectItem value="json">JSON</SelectItem>
                </SelectContent>
              </Select>
              <Button
                variant="outline"
                disabled={reportExport.isPending}
                onClick={() => reportExport.mutate()}
              >
                <Download size={16} aria-hidden="true" />
                {reportExport.isPending
                  ? "Формируем…"
                  : "Сохранить отчёт"}
              </Button>
            </div>
            <Button asChild>
              <Link href="/imports">Импортировать данные</Link>
            </Button>
          </div>
        }
      />

      {reportExport.isError ? (
        <p className="report-export-error" role="alert">
          Не удалось сохранить отчёт: {errorMessage(reportExport.error)}
        </p>
      ) : null}

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

      {summary.data ? (
        <section className="value-evidence" aria-label="Доказанная полезность">
          <div>
            <Clock3 size={20} aria-hidden="true" />
            <span>Оценка экономии времени</span>
            <strong>{summary.data.estimated_hours_saved} ч</strong>
          </div>
          <div>
            <CheckCircle2 size={20} aria-hidden="true" />
            <span>Подтверждённых выполнений</span>
            <strong>
              {summary.data.completed_task_count} из{" "}
              {summary.data.value_observation_count}
            </strong>
          </div>
          <p>
            Это не расчёт ROI: показатель строится только по переданным{" "}
            <code>task_completed</code> и <code>estimated_minutes_saved</code>.
          </p>
        </section>
      ) : null}

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

      <Card className="category-summary-section">
        <CardHeader>
          <CardTitle>Что стоит за категориями</CardTitle>
          <CardDescription>
            Зачем сотрудники используют ИИ, какие формулировки типичны и где
            возникают сложности
          </CardDescription>
        </CardHeader>
        <CardContent>
          {categorySummaries.isPending ? (
            <LoadingBlock rows={5} />
          ) : categorySummaries.isError ? (
            <ErrorState
              message={errorMessage(categorySummaries.error)}
              onRetry={() => categorySummaries.refetch()}
            />
          ) : categorySummaries.data.items.length === 0 ? (
            <EmptyState
              title="Саммари категорий пока нет"
              description="Они появятся после анализа запросов."
            />
          ) : (
            <div className="category-summary-grid">
              {categorySummaries.data.items.map((item) => (
                <article key={item.category}>
                  <div>
                    <CategoryBadge value={item.category} />
                    <strong>{item.percentage}%</strong>
                  </div>
                  <p>{item.summary}</p>
                  {item.representative_queries[0] ? (
                    <blockquote>«{item.representative_queries[0]}»</blockquote>
                  ) : null}
                  {item.top_problems[0] ? (
                    <span>Частая сложность: {item.top_problems[0]}</span>
                  ) : null}
                </article>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

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
                description="Передавайте team, direction и user_id. Для оценки полезности нужны task_completed, estimated_minutes_saved, response, execution_status или rating."
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
                          {item.task_completion_rate === null
                            ? "—"
                            : `${item.task_completion_rate}%`}
                        </strong>
                        <span>задач выполнено</span>
                      </div>
                      <div>
                        <strong>{item.estimated_hours_saved} ч</strong>
                        <span>оценка экономии</span>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </section>

      <Card className="decision-section">
        <CardHeader className="section-card-header">
          <div>
            <CardTitle>Что делать дальше</CardTitle>
            <CardDescription>
              Решения на основе повторяемости запросов, проблем пользователей и
              наблюдаемых результатов агентов
            </CardDescription>
          </div>
          <Sparkles size={20} aria-hidden="true" />
        </CardHeader>
        <CardContent>
          {decisionSupport.isPending ? (
            <LoadingBlock rows={6} />
          ) : decisionSupport.isError ? (
            <ErrorState
              message={errorMessage(decisionSupport.error)}
              onRetry={() => decisionSupport.refetch()}
            />
          ) : (
            <>
              <div className="decision-grid">
                {decisionSupport.data.items.slice(0, 9).map((item, index) => (
                  <article key={`${item.kind}-${item.scope}-${index}`}>
                    <div className="decision-heading">
                      {item.kind === "training" ? (
                        <GraduationCap size={19} aria-hidden="true" />
                      ) : (
                        <Sparkles size={19} aria-hidden="true" />
                      )}
                      <Badge
                        variant={item.priority === "high" ? "warning" : "outline"}
                      >
                        {item.kind === "training"
                          ? "Обучение"
                          : item.kind === "agent"
                            ? "Развитие агента"
                            : "Автоматизация"}
                      </Badge>
                    </div>
                    <h3>{item.title}</h3>
                    <p>{item.evidence}</p>
                    <strong>{item.action}</strong>
                  </article>
                ))}
              </div>
              {decisionSupport.data.data_limitations.length ? (
                <div className="data-limitations">
                  <strong>Что пока нельзя доказать</strong>
                  {decisionSupport.data.data_limitations.map((item) => (
                    <p key={item}>{item}</p>
                  ))}
                </div>
              ) : null}
            </>
          )}
        </CardContent>
      </Card>

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
