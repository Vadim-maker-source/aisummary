"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  CheckCircle2,
  CircleAlert,
  Database,
  FileJson,
  Trash2,
  UploadCloud,
  X,
} from "lucide-react";
import Link from "next/link";
import { useRef, useState } from "react";
import {
  ErrorState,
  LoadingBlock,
  PageHeader,
  errorMessage,
} from "@/components/ui";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { getImportStatus, resetAnalytics, uploadImport } from "@/lib/api";
import { IMPORT_STATUS_LABELS } from "@/lib/constants";
import type { ImportStatus } from "@/types/api";

const MAX_FILE_BYTES = 512 * 1024 * 1024;
const SUPPORTED_EXTENSIONS = new Set(["json", "jsonl", "txt"]);

const STATUS_VARIANTS: Record<
  ImportStatus,
  "secondary" | "warning" | "default" | "destructive"
> = {
  pending: "secondary",
  processing: "warning",
  completed: "default",
  failed: "destructive",
};

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

function formatFileSize(bytes: number): string {
  if (bytes >= 1024 * 1024) {
    return `${(bytes / 1024 / 1024).toLocaleString("ru-RU", {
      maximumFractionDigits: 1,
    })} МБ`;
  }
  return `${(bytes / 1024).toLocaleString("ru-RU", {
    maximumFractionDigits: 1,
  })} КБ`;
}

export default function ImportsPage() {
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [validationError, setValidationError] = useState("");
  const [importId, setImportId] = useState<string | null>(null);
  const upload = useMutation({
    mutationFn: uploadImport,
    onSuccess: (data) => setImportId(data.id),
  });
  const reset = useMutation({
    mutationFn: resetAnalytics,
    onSuccess: async () => {
      setImportId(null);
      setFile(null);
      setValidationError("");
      upload.reset();
      if (inputRef.current) inputRef.current.value = "";
      await queryClient.invalidateQueries();
    },
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

    const extension = selected.name.toLowerCase().split(".").pop() ?? "";
    if (!SUPPORTED_EXTENSIONS.has(extension)) {
      setFile(null);
      setValidationError("Поддерживаются файлы .json, .jsonl и .txt");
      if (inputRef.current) inputRef.current.value = "";
      return;
    }
    if (selected.size > MAX_FILE_BYTES) {
      setFile(null);
      setValidationError("Размер файла не должен превышать 512 МБ");
      if (inputRef.current) inputRef.current.value = "";
      return;
    }
    setFile(selected);
  }

  function removeFile() {
    selectFile(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  function handleDrop(event: React.DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsDragging(false);
    selectFile(event.dataTransfer.files?.[0] ?? null);
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
    <div className="imports-page">
      <PageHeader
        eyebrow="Источник данных"
        title="Импорт логов"
        description="Загрузите историю обращений к ИИ-агентам. После проверки формата система классифицирует запросы и пересоберёт сценарии."
        action={
          <Button variant="outline" asChild>
            <Link href="/dashboard">
              Вернуться к обзору
              <ArrowRight size={16} aria-hidden="true" />
            </Link>
          </Button>
        }
      />

      <section className="import-flow" aria-label="Этапы обработки">
        <div>
          <span>1</span>
          <p>
            <strong>Загрузка</strong>
            JSON, JSONL или TXT до 512 МБ
          </p>
        </div>
        <div>
          <span>2</span>
          <p>
            <strong>Проверка</strong>
            Построчная валидация событий
          </p>
        </div>
        <div>
          <span>3</span>
          <p>
            <strong>Анализ</strong>
            Категории, проблемы и сценарии
          </p>
        </div>
      </section>

      <div className="import-workspace">
        <Card className="import-upload-card">
          <CardHeader>
            <div className="import-card-heading">
              <span className="import-card-icon" aria-hidden="true">
                <UploadCloud size={20} />
              </span>
              <div>
                <CardTitle>Загрузите файл событий</CardTitle>
                <CardDescription>
                  Для больших запросов на 100k токенов используйте JSONL.
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <form className="import-form" onSubmit={submit}>
              <label
                className={`import-dropzone${isDragging ? " is-dragging" : ""}`}
                onDragEnter={(event) => {
                  event.preventDefault();
                  setIsDragging(true);
                }}
                onDragOver={(event) => event.preventDefault()}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
              >
                <input
                  ref={inputRef}
                  type="file"
                  name="file"
                  accept=".json,.jsonl,.txt,application/json,text/plain"
                  onChange={(event) =>
                    selectFile(event.target.files?.[0] ?? null)
                  }
                />
                <span className="import-dropzone-icon" aria-hidden="true">
                  <FileJson size={28} />
                </span>
                <strong>
                  {isDragging
                    ? "Отпустите файл здесь"
                    : "Перетащите файл или выберите на компьютере"}
                </strong>
                <small>JSON · JSONL · TXT — максимальный размер 512 МБ</small>
              </label>

              {file ? (
                <div className="selected-import-file">
                  <FileJson size={20} aria-hidden="true" />
                  <div>
                    <strong>{file.name}</strong>
                    <span>{formatFileSize(file.size)}</span>
                  </div>
                  <button
                    type="button"
                    onClick={removeFile}
                    aria-label="Убрать выбранный файл"
                  >
                    <X size={17} aria-hidden="true" />
                  </button>
                </div>
              ) : null}

              {validationError ? (
                <p className="import-validation-error" role="alert">
                  <CircleAlert size={16} aria-hidden="true" />
                  {validationError}
                </p>
              ) : null}
              {upload.isError ? (
                <ErrorState message={errorMessage(upload.error)} />
              ) : null}

              <div className="import-form-footer">
                <p>
                  Повторная загрузка события с тем же external_id не создаст
                  дубликат.
                </p>
                <Button type="submit" disabled={!file || upload.isPending}>
                  {upload.isPending ? "Загружаем…" : "Запустить импорт"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <Card className="import-requirements-card">
          <CardHeader>
            <div className="import-card-heading">
              <span className="import-card-icon" aria-hidden="true">
                <Database size={20} />
              </span>
              <div>
                <CardTitle>Что должно быть в данных</CardTitle>
                <CardDescription>
                  Минимальный и рекомендуемый состав события.
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="import-requirements">
              <div>
                <Badge variant="default">Обязательно</Badge>
                <p>
                  <strong>Сообщения запроса</strong>
                  <span>
                    request.messages или messages верхнего уровня хотя бы с
                    одним сообщением пользователя.
                  </span>
                </p>
              </div>
              <div>
                <Badge variant="secondary">Для разрезов</Badge>
                <p>
                  <strong>Команда и направление</strong>
                  <span>
                    agent_id, user_id, team и direction позволяют сравнивать
                    эффективность внедрения.
                  </span>
                </p>
              </div>
              <div>
                <Badge variant="outline">Для качества</Badge>
                <p>
                  <strong>Ответ и результат</strong>
                  <span>
                    response, execution_status, latency_ms и rating нужны для
                    анализа проблем агента.
                  </span>
                </p>
              </div>
            </div>
            <div className="import-format-note">
              <CheckCircle2 size={18} aria-hidden="true" />
              <p>
                <strong>OpenAI-compatible формат поддерживается</strong>
                Можно передавать сырой объект запроса и ответ с choices и usage.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {importId ? (
        <Card className="import-progress-card" aria-labelledby="status-title">
          <CardHeader>
            <div className="import-status-heading">
              <div>
                <CardTitle id="status-title">Обработка файла</CardTitle>
                <CardDescription>
                  Статус обновляется автоматически каждые 2 секунды.
                </CardDescription>
              </div>
              {status.data ? (
                <Badge variant={STATUS_VARIANTS[status.data.status]}>
                  {IMPORT_STATUS_LABELS[status.data.status]}
                </Badge>
              ) : null}
            </div>
          </CardHeader>
          <CardContent>
            {status.isPending ? (
              <LoadingBlock rows={4} />
            ) : status.isError ? (
              <ErrorState
                message={errorMessage(status.error)}
                onRetry={() => status.refetch()}
              />
            ) : (
              <>
                <div className="import-progress-meta">
                  <div>
                    <span>Файл</span>
                    <strong>{status.data.filename}</strong>
                  </div>
                  <div>
                    <span>Всего</span>
                    <strong>{status.data.total_rows}</strong>
                  </div>
                  <div>
                    <span>Обработано</span>
                    <strong>{status.data.processed_rows}</strong>
                  </div>
                  <div>
                    <span>Ошибки</span>
                    <strong
                      className={
                        status.data.failed_rows ? "danger-text" : undefined
                      }
                    >
                      {status.data.failed_rows}
                    </strong>
                  </div>
                </div>
                <div className="import-progress-row">
                  <Progress value={progress} aria-label="Прогресс импорта" />
                  <strong>{progress}%</strong>
                </div>

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
                  <div className="import-result is-success">
                    <div>
                      <CheckCircle2 size={20} aria-hidden="true" />
                      <p>
                        <strong>Импорт завершён</strong>
                        События сохранены, фоновый анализ уже запущен.
                      </p>
                    </div>
                    <Button asChild>
                      <Link href="/dashboard">
                        Смотреть аналитику
                        <ArrowRight size={16} aria-hidden="true" />
                      </Link>
                    </Button>
                  </div>
                ) : null}
                {status.data.status === "failed" ? (
                  <div className="import-result is-failed" role="alert">
                    <div>
                      <CircleAlert size={20} aria-hidden="true" />
                      <p>
                        <strong>Импорт завершился с ошибкой</strong>
                        Исправьте строки из журнала и загрузите файл повторно.
                      </p>
                    </div>
                  </div>
                ) : null}
              </>
            )}
          </CardContent>
        </Card>
      ) : null}

      <Card className="data-reset-card">
        <CardHeader>
          <div className="import-card-heading">
            <span className="import-card-icon is-danger" aria-hidden="true">
              <Trash2 size={20} />
            </span>
            <div>
              <CardTitle>Сброс аналитических данных</CardTitle>
              <CardDescription>
                Подготовьте чистую базу перед загрузкой нового демонстрационного
                набора.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="data-reset-row">
            <p>
              Будут удалены события, результаты классификации, сценарии и
              история импортов. Таблицы PostgreSQL и миграции сохранятся.
            </p>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive" disabled={reset.isPending}>
                  <Trash2 size={16} aria-hidden="true" />
                  {reset.isPending ? "Сбрасываем…" : "Сбросить базу"}
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>
                    Удалить все аналитические данные?
                  </AlertDialogTitle>
                  <AlertDialogDescription>
                    Действие нельзя отменить. После сброса дашборд будет пустым,
                    пока вы не импортируете новый файл.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel asChild>
                    <Button variant="outline">Отмена</Button>
                  </AlertDialogCancel>
                  <AlertDialogAction asChild>
                    <Button
                      variant="destructive"
                      onClick={() => reset.mutate()}
                    >
                      Да, удалить данные
                    </Button>
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
          {reset.isError ? (
            <ErrorState message={errorMessage(reset.error)} />
          ) : null}
          {reset.data ? (
            <div className="data-reset-success" role="status">
              <CheckCircle2 size={18} aria-hidden="true" />
              Удалено событий: {reset.data.deleted_events}. База готова к
              новому импорту.
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
