BEGIN;

CREATE TABLE IF NOT EXISTS imports (
    id uuid PRIMARY KEY,
    filename varchar(255) NOT NULL,
    status varchar(32) NOT NULL,
    total_rows integer NOT NULL DEFAULT 0,
    processed_rows integer NOT NULL DEFAULT 0,
    failed_rows integer NOT NULL DEFAULT 0,
    error_log jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz NULL
);

CREATE TABLE IF NOT EXISTS agent_events (
    id uuid PRIMARY KEY,
    external_id varchar(255) NOT NULL,
    agent_id varchar(255) NOT NULL,
    import_id uuid NULL REFERENCES imports(id) ON DELETE SET NULL,
    model varchar(255) NULL,
    stream boolean NOT NULL DEFAULT false,
    raw_request jsonb NOT NULL,
    raw_response jsonb NULL,
    agent_answer text NULL,
    execution_status varchar(32) NOT NULL,
    latency_ms integer NULL,
    rating numeric(2,1) NULL,
    prompt_tokens integer NULL,
    completion_tokens integer NULL,
    total_tokens integer NULL,
    occurred_at timestamptz NULL,
    received_at timestamptz NOT NULL DEFAULT now(),
    analysis_status varchar(32) NOT NULL,
    analysis_error text NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_event_agent_external UNIQUE (agent_id, external_id),
    CONSTRAINT ck_latency CHECK (latency_ms IS NULL OR latency_ms >= 0),
    CONSTRAINT ck_rating CHECK (
        rating IS NULL OR (rating >= 1 AND rating <= 5)
    )
);

CREATE INDEX IF NOT EXISTS ix_events_analysis_status
    ON agent_events (analysis_status);
CREATE INDEX IF NOT EXISTS ix_events_import_id
    ON agent_events (import_id);
CREATE INDEX IF NOT EXISTS ix_events_occurred_at
    ON agent_events (occurred_at);

CREATE TABLE IF NOT EXISTS event_analyses (
    id uuid PRIMARY KEY,
    event_id uuid NOT NULL UNIQUE
        REFERENCES agent_events(id) ON DELETE CASCADE,
    effective_user_query text NOT NULL,
    category varchar(64) NOT NULL,
    classification_confidence numeric(4,3) NOT NULL,
    query_problem_reasons jsonb NOT NULL DEFAULT '[]'::jsonb,
    automation_potential varchar(16) NOT NULL,
    warnings jsonb NOT NULL DEFAULT '[]'::jsonb,
    classifier_version varchar(64) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_analyses_category
    ON event_analyses (category);
CREATE INDEX IF NOT EXISTS ix_analyses_created_at
    ON event_analyses (created_at);

CREATE TABLE IF NOT EXISTS analysis_runs (
    id uuid PRIMARY KEY,
    trigger_import_id uuid NULL UNIQUE
        REFERENCES imports(id) ON DELETE SET NULL,
    status varchar(32) NOT NULL,
    algorithm_version varchar(64) NOT NULL,
    is_current boolean NOT NULL DEFAULT false,
    error_message text NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz NULL
);

CREATE INDEX IF NOT EXISTS ix_analysis_runs_current
    ON analysis_runs (is_current);
CREATE INDEX IF NOT EXISTS ix_analysis_runs_status
    ON analysis_runs (status);

CREATE TABLE IF NOT EXISTS scenarios (
    id uuid PRIMARY KEY,
    analysis_run_id uuid NOT NULL
        REFERENCES analysis_runs(id) ON DELETE CASCADE,
    category varchar(64) NOT NULL,
    name varchar(255) NOT NULL,
    summary text NOT NULL,
    representative_queries jsonb NOT NULL DEFAULT '[]'::jsonb,
    common_problems jsonb NOT NULL DEFAULT '[]'::jsonb,
    automation_potential varchar(16) NOT NULL,
    suggested_action text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_scenarios_run_category
    ON scenarios (analysis_run_id, category);

CREATE TABLE IF NOT EXISTS scenario_members (
    scenario_id uuid NOT NULL
        REFERENCES scenarios(id) ON DELETE CASCADE,
    event_id uuid NOT NULL
        REFERENCES agent_events(id) ON DELETE CASCADE,
    similarity numeric(4,3) NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (scenario_id, event_id)
);

CREATE INDEX IF NOT EXISTS ix_scenario_members_event
    ON scenario_members (event_id);

CREATE TABLE IF NOT EXISTS alembic_version (
    version_num varchar(32) NOT NULL PRIMARY KEY
);

INSERT INTO alembic_version (version_num)
VALUES ('20260724_0001')
ON CONFLICT (version_num) DO NOTHING;

COMMIT;

