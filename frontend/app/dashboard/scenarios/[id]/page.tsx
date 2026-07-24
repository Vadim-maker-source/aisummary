"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  AutomationBadge,
  CategoryBadge,
  ErrorState,
  LoadingBlock,
  PageHeader,
  errorMessage,
} from "@/components/ui";
import { ApiError, getScenario } from "@/lib/api";

export default function ScenarioDetailPage() {
  const params = useParams<{ id: string }>();
  const scenario = useQuery({
    queryKey: ["scenario", params.id],
    queryFn: () => getScenario(params.id),
  });

  if (scenario.isPending) {
    return (
      <>
        <PageHeader
          eyebrow="Карточка сценария"
          title="Загружаем сценарий"
          description="Собираем сводку и типичные формулировки."
        />
        <section className="panel">
          <LoadingBlock rows={7} />
        </section>
      </>
    );
  }

  if (scenario.isError) {
    const notFound =
      scenario.error instanceof ApiError && scenario.error.status === 404;
    return (
      <>
        <PageHeader
          eyebrow="Карточка сценария"
          title={notFound ? "Сценарий не найден" : "Не удалось открыть сценарий"}
          description={
            notFound
              ? "Возможно, после новой группировки сценарий получил другой идентификатор."
              : "Данные временно недоступны."
          }
        />
        <section className="panel">
          {notFound ? (
            <div className="empty-state">
              <div className="empty-symbol" aria-hidden="true">
                404
              </div>
              <h3>Такого сценария нет</h3>
              <p>{errorMessage(scenario.error)}</p>
              <Link className="button primary" href="/dashboard/scenarios">
                ← Вернуться к сценариям
              </Link>
            </div>
          ) : (
            <ErrorState
              message={errorMessage(scenario.error)}
              onRetry={() => scenario.refetch()}
            />
          )}
        </section>
      </>
    );
  }

  const data = scenario.data;

  return (
    <>
      <Link className="back-link" href="/dashboard/scenarios">
        ← Все сценарии
      </Link>
      <PageHeader
        eyebrow="Карточка сценария"
        title={data.name}
        description={data.summary}
        action={
          <div className="badge-row">
            <CategoryBadge value={data.category} />
            <AutomationBadge value={data.automation_potential} />
          </div>
        }
      />

      <div className="detail-stats">
        <article>
          <p>Запросов в сценарии</p>
          <strong>{data.request_count.toLocaleString("ru-RU")}</strong>
        </article>
        <article>
          <p>Типичных формулировок</p>
          <strong>{data.representative_queries.length}</strong>
        </article>
        <article>
          <p>Точек риска</p>
          <strong>{data.common_problems.length}</strong>
        </article>
      </div>

      <div className="detail-grid">
        <section className="panel" aria-labelledby="queries-title">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Голос пользователя</p>
              <h2 id="queries-title">Типичные запросы</h2>
            </div>
          </div>
          <ol className="quote-list">
            {data.representative_queries.map((query, index) => (
              <li key={`${query}-${index}`}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <blockquote>«{query}»</blockquote>
              </li>
            ))}
          </ol>
        </section>

        <div className="detail-side">
          <section className="panel action-panel" aria-labelledby="action-title">
            <p className="panel-kicker">Рекомендация</p>
            <h2 id="action-title">Что автоматизировать</h2>
            <p>{data.suggested_action}</p>
            <div className="action-marker">→</div>
          </section>

          <section className="panel" aria-labelledby="risks-title">
            <p className="panel-kicker">Точки риска</p>
            <h2 id="risks-title">Что стоит уточнять</h2>
            {data.common_problems.length ? (
              <ul className="risk-list">
                {data.common_problems.map((problem) => (
                  <li key={problem}>{problem}</li>
                ))}
              </ul>
            ) : (
              <p className="muted-copy">Типичные проблемы не обнаружены.</p>
            )}
          </section>
        </div>
      </div>
    </>
  );
}
