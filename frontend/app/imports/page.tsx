"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRef, useState } from "react";
import {
  ErrorState,
  LoadingBlock,
  PageHeader,
  errorMessage,
} from "@/components/ui";
import { getImportStatus, uploadImport } from "@/lib/api";
import { IMPORT_STATUS_LABELS } from "@/lib/constants";

function errorDetail(value: unknown): string {
  if (typeof value === "string") return value;
  if (
    typeof value === "object" &&
    value !== null &&
    "detail" in value &&
    typeof value.detail === "string"
  ) {
    const row =
      "row" in value && typeof value.row === "number"
        ? `Строка ${value.row}: `
        : "";
    return `${row}${value.detail}`;
  }
  return JSON.stringify(value);
}

export default function ImportsPage() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [validationError, setValidationError] = useState("");
  const [importId, setImportId] = useState<string | null>(null);
  const upload = useMutation({
    mutationFn: uploadImport,
    onSuccess: (data) => setImportId(data.id),
  });
  const status = useQuery({
    queryKey: ["import-status", importId],
    queryFn: () => getImportStatus(importId!),
    enabled: Boolean(importId),
    refetchInterval: (query) => {
      const currentStatus = query.state.data?.status;
      return currentStatus === "completed" || currentStatus === "failed"
        ? false
        : 2_000;
    },
  });

  function selectFile(selected: File | null) {
    setValidationError("");
    setImportId(null);
    upload.reset();
    if (!selected) {
      setFile(null);
      return;
    }
    const extension = selected.name.toLowerCase().split(".").pop();
    if (extension !== "json" && extension !== "jsonl") {
      setFile(null);
      setValidationError("Поддерживаются только файлы .json и .jsonl");
      if (inputRef.current) inputRef.current.value = "";
      return;
    }
    setFile(selected);
  }

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setValidationError("Выберите файл для импорта");
      return;
    }
    upload.mutate(file);
  }

  const progress = status.data?.total_rows
    ? Math.round(
        ((status.data.processed_rows + status.data.failed_rows) /
          status.data.total_rows) *
          100,
      )
    : 0;

  return (
    <>
      <PageHeader
        eyebrow="Подключение данных"
        title="Импорт событий"
        description="Загрузите историю запросов в формате JSON или JSONL. Анализ запустится в фоне."
        action={
          <Link className="button secondary" href="/dashboard">
            Перейти к обзору →
          </Link>
        }
      />

      <div className="import-layout">
        <section className="panel upload-panel" aria-labelledby="upload-title">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Шаг 1</p>
              <h2 id="upload-title">Выберите файл</h2>
            </div>
          </div>
          <form onSubmit={submit}>
            <label className="dropzone">
              <input
                ref={inputRef}
                type="file"
                name="file"
                accept=".json,.jsonl,application/json"
                onChange={(event) => selectFile(event.target.files?.[0] ?? null)}
              />
              <span className="dropzone-icon" aria-hidden="true">
                ↑
              </span>
              <strong>
                {file ? file.name : "Перетащите файл или нажмите для выбора"}
              </strong>
              <small>
                {file
                  ? `${(file.size / 1024).toLocaleString("ru-RU", {
                      maximumFractionDigits: 1,
                    })} КБ`
                  : "JSON-массив событий или один объект на строку в JSONL"}
              </small>
            </label>
            {validationError ? (
              <p className="field-error" role="alert">
                {validationError}
              </p>
            ) : null}
            {upload.isError ? (
              <ErrorState message={errorMessage(upload.error)} />
            ) : null}
            <div className="form-footer">
              <p>
                Файл отправляется как <code>multipart/form-data</code>, поле{" "}
                <code>file</code>.
              </p>
              <button
                className="button primary"
                type="submit"
                disabled={!file || upload.isPending}
              >
                {upload.isPending ? "Отправляем…" : "Начать импорт"}
              </button>
            </div>
          </form>
        </section>

        <aside className="panel guide-panel" aria-labelledby="guide-title">
          <p className="panel-kicker">Перед загрузкой</p>
          <h2 id="guide-title">Проверка формата</h2>
          <ol>
            <li>
              <span>01</span>
              <p>
                <strong>Идентификаторы</strong>
                external_id и agent_id заполнены
              </p>
            </li>
            <li>
              <span>02</span>
              <p>
                <strong>Сообщения</strong>
                request.messages содержит хотя бы один элемент
              </p>
            </li>
            <li>
              <span>03</span>
              <p>
                <strong>Время</strong>
                occurred_at передаётся в ISO 8601 UTC или null
              </p>
            </li>
          </ol>
        </aside>
      </div>

      {importId ? (
        <section className="panel import-status-panel" aria-labelledby="status-title">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Шаг 2 · обновление каждые 2 секунды</p>
              <h2 id="status-title">Статус импорта</h2>
            </div>
            {status.data ? (
              <span className={`import-status status-${status.data.status}`}>
                {IMPORT_STATUS_LABELS[status.data.status]}
              </span>
            ) : null}
          </div>

          {status.isPending ? (
            <LoadingBlock rows={4} />
          ) : status.isError ? (
            <ErrorState
              message={errorMessage(status.error)}
              onRetry={() => status.refetch()}
            />
          ) : (
            <>
              <div className="progress-meta">
                <div>
                  <p>Файл</p>
                  <strong>{status.data.filename}</strong>
                </div>
                <div>
                  <p>Всего строк</p>
                  <strong>{status.data.total_rows}</strong>
                </div>
                <div>
                  <p>Обработано</p>
                  <strong>{status.data.processed_rows}</strong>
                </div>
                <div>
                  <p>Не обработано</p>
                  <strong className={status.data.failed_rows ? "danger-text" : ""}>
                    {status.data.failed_rows}
                  </strong>
                </div>
              </div>
              <div
                className="progress-track"
                role="progressbar"
                aria-label="Прогресс импорта"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={progress}
              >
                <span style={{ width: `${progress}%` }} />
              </div>
              <p className="progress-caption">{progress}% обработано</p>

              {status.data.errors.length ? (
                <div className="import-errors">
                  <h3>Строки с ошибками</h3>
                  <ul>
                    {status.data.errors.map((item, index) => (
                      <li key={index}>{errorDetail(item)}</li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {status.data.status === "completed" ? (
                <div className="success-banner">
                  <div>
                    <strong>Импорт завершён</strong>
                    <p>События добавлены, фоновый анализ уже запущен.</p>
                  </div>
                  <Link className="button primary" href="/dashboard">
                    Смотреть аналитику →
                  </Link>
                </div>
              ) : null}
              {status.data.status === "failed" ? (
                <div className="failure-banner" role="alert">
                  <strong>Импорт завершился с ошибкой</strong>
                  <p>Проверьте журнал выше и повторите загрузку.</p>
                </div>
              ) : null}
            </>
          )}
        </section>
      ) : null}
    </>
  );
}
