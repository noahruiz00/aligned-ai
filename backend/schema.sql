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
    data        JSON NOT NULL,
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

CREATE INDEX IF NOT EXISTS ix_conversations_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS ix_values_user ON "values"(user_id);
CREATE INDEX IF NOT EXISTS ix_purpose_user ON purpose_statements(user_id);
CREATE INDEX IF NOT EXISTS ix_scores_user ON alignment_scores(user_id);
CREATE INDEX IF NOT EXISTS ix_notes_client ON advisor_notes(client_id);
