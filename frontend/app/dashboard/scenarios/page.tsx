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
  errorMessage,
} from "@/components/ui";
import { getScenarios } from "@/lib/api";
import { CATEGORIES, CATEGORY_LABELS } from "@/lib/constants";
import type { Category } from "@/types/api";

const PAGE_SIZE = 20;

export default function ScenariosPage() {
  const [category, setCategory] = useState<Category | "">("");
  const [page, setPage] = useState(1);
  const scenarios = useQuery({
    queryKey: ["scenarios", category, page],
    queryFn: () =>
      getScenarios({
        category: category || undefined,
        page,
        page_size: PAGE_SIZE,
      }),
  });

  function changeCategory(value: Category | "") {
    setCategory(value);
    setPage(1);
  }

  return (
    <>
      <PageHeader
        eyebrow="Карта повторяемости"
        title="Сценарии"
        description="Группы похожих запросов, найденные автоматически внутри каждой категории."
      />

      <section className="filter-bar" aria-label="Фильтры сценариев">
        <label>
          <span>Категория</span>
          <select
            value={category}
            onChange={(event) =>
              changeCategory(event.target.value as Category | "")
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
        {category ? (
          <button
            className="text-button"
            type="button"
            onClick={() => changeCategory("")}
          >
            Сбросить фильтр
          </button>
        ) : null}
      </section>

      <section className="panel scenario-list-panel" aria-labelledby="scenario-list-title">
        <div className="panel-heading">
          <div>
            <p className="panel-kicker">Приоритетный список</p>
            <h2 id="scenario-list-title">
              {category ? CATEGORY_LABELS[category] : "Все сценарии"}
            </h2>
          </div>
          {scenarios.data ? (
            <span className="count-label">{scenarios.data.total} найдено</span>
          ) : null}
        </div>

        {scenarios.isPending ? (
          <LoadingBlock rows={6} />
        ) : scenarios.isError ? (
          <ErrorState
            message={errorMessage(scenarios.error)}
            onRetry={() => scenarios.refetch()}
          />
        ) : scenarios.data.items.length === 0 ? (
          <EmptyState
            title="Сценариев не найдено"
            description="Попробуйте другую категорию или дождитесь следующей группировки."
            href="/imports"
            actionLabel="Импортировать события"
          />
        ) : (
          <>
            <div className="scenario-cards">
              {scenarios.data.items.map((scenario, index) => (
                <article className="scenario-card" key={scenario.id}>
                  <div className="scenario-rank">
                    {String((page - 1) * PAGE_SIZE + index + 1).padStart(2, "0")}
                  </div>
                  <div className="scenario-main">
                    <div className="badge-row">
                      <CategoryBadge value={scenario.category} />
                      <AutomationBadge value={scenario.automation_potential} />
                    </div>
                    <h3>
                      <Link href={`/dashboard/scenarios/${scenario.id}`}>
                        {scenario.name}
                      </Link>
                    </h3>
                    <p>{scenario.summary}</p>
                    <div className="scenario-meta">
                      <span>
                        <strong>{scenario.request_count}</strong> запросов
                      </span>
                      <span>
                        <strong>{scenario.common_problems.length}</strong> точек
                        риска
                      </span>
                    </div>
                  </div>
                  <div className="scenario-action">
                    <p>Следующий шаг</p>
                    <strong>{scenario.suggested_action}</strong>
                    <Link
                      className="button secondary"
                      href={`/dashboard/scenarios/${scenario.id}`}
                    >
                      Открыть сценарий
                    </Link>
                  </div>
                </article>
              ))}
            </div>
            <Pagination
              page={scenarios.data.page}
              pageSize={scenarios.data.page_size}
              total={scenarios.data.total}
              onPageChange={setPage}
            />
          </>
        )}
      </section>
    </>
  );
}
