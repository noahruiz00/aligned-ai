-- Aligned AI: PostgreSQL schema.
-- The API creates these tables automatically on startup (SQLAlchemy create_all);
-- this file is the reviewable reference and can be applied manually with psql.

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(120) NOT NULL,
    email           VARCHAR(200),
    role            VARCHAR(20)  NOT NULL DEFAULT 'client',      -- client | advisor
    household_type  VARCHAR(20)  NOT NULL DEFAULT 'individual',  -- individual | couple | family
    advisor_id      INTEGER REFERENCES users(id),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS conversations (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    messages    JSON    NOT NULL DEFAULT '[]',   -- [{role, content, stage}]
    status      VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Structured values profile extracted from a conversation
CREATE TABLE IF NOT EXISTS "values" (
    id               SERIAL PRIMARY KEY,
    user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id  INTEGER REFERENCES conversations(id) ON DELETE SET NULL,
    data             JSON NOT NULL,  -- {values, financial_priorities, life_goals, family_goals, legacy_goals, philanthropy, emotional_cues, money_script}
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS purpose_statements (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    data        JSON NOT NULL,            -- legacy shape, derived from sections for new drafts
    sections    JSON,                     -- {vision, money_role, ... : {text, insight_ids}} DRAFT
    status      VARCHAR(20) NOT NULL DEFAULT 'draft',  -- draft | legacy
    version     INTEGER NOT NULL DEFAULT 1,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS alignment_scores (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    overall     INTEGER NOT NULL,
    categories  JSON NOT NULL,  -- {cash_flow|investment|estate|philanthropy|risk: {score, label, question, explanation, recommendations, weight}}
    portrait    JSON NOT NULL,  -- financial snapshot the score was computed from
    insights    JSON,           -- AI-generated advisor insights
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS advisor_notes (
    id          SERIAL PRIMARY KEY,
    client_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    advisor_id  INTEGER REFERENCES users(id) ON DELETE SET NULL,
    body        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Discovery methodology (editable business IP) --------------------------------
CREATE TABLE IF NOT EXISTS methodology_modules (
    id             SERIAL PRIMARY KEY,
    key            VARCHAR(40)  NOT NULL UNIQUE,
    title          VARCHAR(80)  NOT NULL,
    description    TEXT NOT NULL DEFAULT '',
    intro          TEXT NOT NULL DEFAULT '',
    "order"        INTEGER NOT NULL DEFAULT 0,
    session_group  INTEGER NOT NULL DEFAULT 1,   -- suggested sitting
    follow_up_mode VARCHAR(10) NOT NULL DEFAULT 'pool',  -- pool | compose
    active         BOOLEAN NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS methodology_questions (
    id                  SERIAL PRIMARY KEY,
    module_id           INTEGER NOT NULL REFERENCES methodology_modules(id) ON DELETE CASCADE,
    key                 VARCHAR(60) NOT NULL UNIQUE,
    section             VARCHAR(160) NOT NULL DEFAULT '',  -- heading within the module
    prompt              TEXT NOT NULL,
    follow_up_guidance  TEXT NOT NULL DEFAULT '',
    classification      VARCHAR(12) NOT NULL DEFAULT 'core',  -- core | follow_up | optional | inactive
    required            BOOLEAN NOT NULL DEFAULT TRUE,
    max_follow_ups      INTEGER NOT NULL DEFAULT 1,
    "order"             INTEGER NOT NULL DEFAULT 0,
    active              BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Discovery sessions and answers -------------------------------------------------
CREATE TABLE IF NOT EXISTS discovery_sessions (
    id                   SERIAL PRIMARY KEY,
    user_id              INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token                VARCHAR(64) UNIQUE,                       -- unguessable resume token; the only public handle
    status               VARCHAR(20) NOT NULL DEFAULT 'active',   -- active | paused | complete
    sharing              VARCHAR(24) NOT NULL DEFAULT 'private',  -- private | pending_share | shared_with_advisor
    rejected_insight_count INTEGER NOT NULL DEFAULT 0,            -- QA only: AI items discarded by validation
    extraction_runs      INTEGER NOT NULL DEFAULT 0,
    current_question_id  INTEGER REFERENCES methodology_questions(id) ON DELETE SET NULL,
    module_reflections   JSON NOT NULL DEFAULT '{}',   -- {module_key: {summary, themes, feedback, correction}}
    opted_modules        JSON,                          -- modules the client chose to go deeper into
    conversation_id      INTEGER REFERENCES conversations(id) ON DELETE SET NULL,
    started_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_activity_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at         TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS answers (
    id                SERIAL PRIMARY KEY,
    session_id        INTEGER NOT NULL REFERENCES discovery_sessions(id) ON DELETE CASCADE,
    user_id           INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question_id       INTEGER NOT NULL REFERENCES methodology_questions(id),
    parent_answer_id  INTEGER REFERENCES answers(id) ON DELETE CASCADE,  -- set on follow-up answers
    prompt_text       TEXT NOT NULL,          -- exact wording shown
    text              TEXT NOT NULL DEFAULT '',
    skipped           BOOLEAN NOT NULL DEFAULT FALSE,
    skip_reason       VARCHAR(20),           -- skip | prefer_not
    input_mode        VARCHAR(10) NOT NULL DEFAULT 'text',
    ai_reflection     TEXT,
    ai_follow_up      TEXT,
    follow_up_question_id INTEGER REFERENCES methodology_questions(id),  -- when the follow-up came from the pool
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Structured understanding --------------------------------------------------------
CREATE TABLE IF NOT EXISTS client_insights (
    id                 SERIAL PRIMARY KEY,
    client_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id         INTEGER REFERENCES discovery_sessions(id) ON DELETE SET NULL,
    module_key         VARCHAR(40) NOT NULL DEFAULT '',
    type               VARCHAR(40) NOT NULL,     -- personal_values | financial_values | goals | ... | open_questions
    label              VARCHAR(120) NOT NULL,
    summary            TEXT NOT NULL,
    basis              VARCHAR(24) NOT NULL DEFAULT 'ai_interpretation',  -- client_fact | client_statement | ai_interpretation
    confidence         DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    status             VARCHAR(24) NOT NULL DEFAULT 'ai_detected',  -- ai_detected | needs_clarification | client_confirmed | client_corrected | advisor_confirmed
    original           JSON NOT NULL,            -- AI output as first produced; never edited
    client_feedback    VARCHAR(16),              -- accurate | partly | edit | clarify
    client_correction  TEXT,
    active             BOOLEAN NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS evidence_links (
    id           SERIAL PRIMARY KEY,
    insight_id   INTEGER NOT NULL REFERENCES client_insights(id) ON DELETE CASCADE,
    question_id  INTEGER NOT NULL REFERENCES methodology_questions(id),
    answer_id    INTEGER NOT NULL REFERENCES answers(id) ON DELETE CASCADE,
    module       VARCHAR(80) NOT NULL,
    section      VARCHAR(160) NOT NULL DEFAULT '',
    excerpt      TEXT NOT NULL,            -- verbatim from the answer
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS insight_events (
    id          SERIAL PRIMARY KEY,
    insight_id  INTEGER NOT NULL REFERENCES client_insights(id) ON DELETE CASCADE,
    event       VARCHAR(24) NOT NULL,      -- ai_detected | re_extracted | client_feedback | advisor_confirmed
    before      JSON,
    after       JSON,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_conversations_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS ix_values_user ON "values"(user_id);
CREATE INDEX IF NOT EXISTS ix_purpose_user ON purpose_statements(user_id);
CREATE INDEX IF NOT EXISTS ix_scores_user ON alignment_scores(user_id);
CREATE INDEX IF NOT EXISTS ix_notes_client ON advisor_notes(client_id);
CREATE INDEX IF NOT EXISTS ix_questions_module ON methodology_questions(module_id);
CREATE INDEX IF NOT EXISTS ix_sessions_user ON discovery_sessions(user_id);
CREATE INDEX IF NOT EXISTS ix_answers_session ON answers(session_id);
CREATE INDEX IF NOT EXISTS ix_answers_question ON answers(question_id);
CREATE INDEX IF NOT EXISTS ix_insights_client ON client_insights(client_id);
CREATE INDEX IF NOT EXISTS ix_evidence_insight ON evidence_links(insight_id);
CREATE INDEX IF NOT EXISTS ix_evidence_answer ON evidence_links(answer_id);
