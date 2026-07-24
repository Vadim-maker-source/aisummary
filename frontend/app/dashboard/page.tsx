"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  CheckCircle2,
  CircleAlert,
  Layers3,
  MessagesSquare,
} from "lucide-react";
import Link from "next/link";
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
  getScenarios,
} from "@/lib/api";
import { CATEGORY_LABELS } from "@/lib/constants";

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
        eyebrow="Обзор"
        title="Аналитика запросов"
        description="Распределение запросов по задачам и сценариям во всей загруженной выборке."
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
                <p className="metric-caption">сгруппированных способов использования</p>
              </CardContent>
            </Card>
          </section>

          <div className="sample-status" aria-label="Состояние обработки">
            <span>Состояние выборки</span>
            <Badge variant="outline">
              Ожидают: {summary.data.pending_requests}
            </Badge>
            <Badge
              variant={summary.data.failed_requests ? "destructive" : "outline"}
            >
              Ошибки: {summary.data.failed_requests}
            </Badge>
            <Badge
              variant={
                summary.data.unclassified_count ? "warning" : "outline"
              }
            >
              Без категории: {summary.data.unclassified_count}
            </Badge>
          </div>
        </>
      )}

      <section className="overview-grid" aria-label="Распределение и качество данных">
        <Card>
          <CardHeader className="section-card-header">
            <div>
              <CardTitle>Категории запросов</CardTitle>
              <CardDescription>
                Частота задач во всей загруженной выборке
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
            <CardTitle>Как читать отчёт</CardTitle>
            <CardDescription>
              Показатели рассчитаны по загруженным запросам
            </CardDescription>
          </CardHeader>
          <CardContent className="report-notes">
            <div>
              <strong>Категория</strong>
              <p>Тип задачи: поиск, анализ данных, подготовка текста и другие.</p>
            </div>
            <div>
              <strong>Сценарий</strong>
              <p>Группа похожих запросов внутри одной категории.</p>
            </div>
            <div>
              <strong>Требует внимания</strong>
              <p>Неоднозначный запрос, нехватка контекста или несколько задач сразу.</p>
            </div>
            <div>
              <strong>Автоматизация</strong>
              <p>Оценка того, насколько сценарий подходит для повторяемого процесса.</p>
            </div>
          </CardContent>
        </Card>
      </section>

      <Card className="scenarios-section">
        <CardHeader className="section-card-header">
          <div>
            <CardTitle>Частые сценарии</CardTitle>
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
