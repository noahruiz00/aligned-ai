# Aligned AI — Wealth Purpose Companion

A working prototype of Aligned Capital Management's Wealth Purpose methodology:

**Discover → Harvest → Architect → Steward**

1. **Discover / Harvest.** A guided AI conversation about the purpose of wealth, a meaningful life, the
   family money story, values, causes, and legacy.
2. **Values extraction.** Claude turns the conversation into a structured profile: values, financial priorities,
   goals, philanthropy, emotional cues, and money script.
3. **Architect.** A Wealth Purpose Statement report with purpose, core values, life vision, philosophy, legacy,
   accountability measures, and how it guides investments, estate, giving, and cash flow. It exports to PDF.
4. **Steward.** A short financial portrait feeds a **Wealth Alignment Score** across cash flow, investment,
   estate & legacy, philanthropy, and risk.
5. **Advisor view.** Book of families, client brief, AI meeting-prep insights, values profile, transcript, and
   private notes.

Three separate AI engines: conversation (chooses the follow-up), extraction (structured, evidence-linked
insights under a strict JSON schema, validated server-side) and synthesis (the readable draft). Every insight keeps
whether it is a client fact, a client statement or an AI interpretation, and nothing becomes "confirmed" until the
client says so. The AI supports the advisor; it never gives the client financial advice. The alignment score is
**deterministic and explainable**: every point traces to an input, and the client's own values change the
weighting. Claude writes the language (conversation, statement, insights), not the numbers.

```
frontend/   Next.js 14 (App Router) · TypeScript · Tailwind · Framer Motion
backend/    FastAPI · SQLAlchemy · PostgreSQL (SQLite fallback) · Anthropic SDK
```

---

## 1. Installation

Prerequisites: Python 3.11+, Node 18+, and optionally PostgreSQL 14+.

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env              # then edit
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
cp .env.example .env.local
npm run dev                       # http://localhost:3000
```

On first start the API creates its tables and seeds a demo book of three fictional families.

## 2. Environment variables

**backend/.env**

| Variable | Default | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | empty | OpenRouter credentials (backend only). If empty, the app runs in **demo mode** with a deterministic stand-in. |
| `OPENROUTER_MODEL` | `openai/gpt-5.6-luna` | Model used for every AI step |
| `DEMO_MODE` | `false` | Force demo mode even with a key (offline rehearsals) |
| `DATABASE_URL` | SQLite `backend/aligned.db` | e.g. `postgresql+psycopg://user:pass@localhost:5432/aligned` (`postgres://` URLs are accepted) |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated frontend origins |
| `APP_ENV` | `development` | `production` turns on Secure cookies and refuses to start without the three values below |
| `SECRET_KEY` | generated per process in development | Signs staff session cookies. Required in production (`python -c "import secrets; print(secrets.token_hex(32))"`) |
| `ADMIN_PASSWORD` / `ADVISOR_PASSWORD` | empty | Staff passwords for `/login`. admin can do everything an advisor can, plus edit the methodology. One of them is required in production |
| `ALLOW_DEMO_IN_PRODUCTION` | empty | Only for a stand-in-AI rehearsal on a production deployment; real beta runs leave it unset |
| `STAFF_SESSION_HOURS` | `12` | Staff sign-in lifetime |

**frontend/.env.local**

| Variable | Default | Purpose |
|---|---|---|
| `API_URL` | `http://localhost:8000` | Where Next.js proxies `/api/*` (server-side). The browser only ever talks to the frontend origin, so the HttpOnly cookies stay first-party |
| `NEXT_PUBLIC_API_URL` | unset (`/api`) | Leave unset. Pointing the browser straight at a different origin breaks cookie-based sign-in |

**Demo vs. real beta.** With no `OPENROUTER_API_KEY` (or `DEMO_MODE=true`) every AI step uses a deterministic
stand-in and the UI says so. With a key configured the app is in strict mode: a model failure shows an honest error
(reflection "saved", review page "try again") and never substitutes stand-in insights for a real client.
`GET /health` reports `demo_mode` and `app_env`; the admin page shows a mode banner.

**Access.** Clients have no account: starting a discovery sets an HttpOnly cookie holding an unguessable resume token,
and their private link `/discover/resume/{token}` is the only way to reopen it elsewhere. Staff sign in at `/login`
with `ADVISOR_PASSWORD` or `ADMIN_PASSWORD` (HttpOnly, SameSite=Lax, Secure in production, 12h). Nothing a client
writes is visible to the advisor until the client presses **Share my profile** on the review page.

## 3. Database setup (PostgreSQL)

```bash
createdb aligned
# either let the API create tables on startup, or apply the reference schema:
psql -d aligned -f backend/schema.sql
```

Tables: `users`, `conversations`, `values`, `purpose_statements`, `alignment_scores`, `advisor_notes`, the
discovery tables `methodology_modules`, `methodology_questions`, `discovery_sessions`, `answers`, and the
understanding tables `client_insights` (typed, evidence-linked, with status and the original AI output),
`evidence_links` (question, answer, module, section, verbatim excerpt) and `insight_events` (audit history). The methodology
(a 2-question beta opening module plus 7 modules, 25 section headings and 104 questions transcribed verbatim in
`backend/app/methodology_source.py`) is loaded once and edited afterwards at `/admin/methodology`; it is data, not
UI text. Each question is classified `core` (asked by default: 20), `follow_up` (the AI may ask it once after a core
question in the same section: 24), `optional` (offered as "go deeper" after a module: 61) or `inactive` (kept, never
shown: 1). The approved classification is applied once to a never-classified database; after that the admin editor
is authoritative. Columns added after a table first shipped are applied at startup by `ensure_columns()` in `app/db.py`.
To reseed with SQLite, delete `backend/aligned.db` and restart.

## 4. API

Interactive docs are at `http://localhost:8000/docs`.

| Method | Path | Body / query | Returns |
|---|---|---|---|
| `POST` | `/discovery/start` | `{name, household_type}` | Discovery state: session, 10 steps with progress, current module + question |
| `GET` | `/discovery/{id}` | | Resume a session (state) |
| `POST` | `/discovery/{id}/answer` | `{question_id, text, parent_answer_id?}` | `{turn: {reflection, follow_up, module_completed, suggest_pause}, state}` |
| `POST` | `/discovery/{id}/skip` · `/back` · `/next` · `/goto` · `/pause` | | Navigation; every call returns the state |
| `POST` | `/discovery/{id}/reflections/{module}/feedback` | `{feedback: yes\|partly\|edit, correction?}` | Client confirms or corrects "what we're hearing" |
| `POST` | `/discovery/{id}/complete` | | Final extraction pass, drafts the sectioned Wealth Purpose Statement, derives the legacy values/purpose records |
| `GET` | `/discovery/{id}/insights` | | The client's structured insights, each with evidence links and history |
| `POST` | `/discovery/{id}/insights/{iid}/feedback` | `{feedback: accurate\|partly\|edit\|clarify, text?}` | Client confirms or corrects; the original AI output is kept |
| `POST` | `/discovery/{id}/insights/refresh` | | Re-run extraction over everything answered so far |
| `GET` | `/methodology` | | Active modules and questions (clients) |
| `GET/POST/PUT/DELETE` | `/admin/methodology/...` | modules, questions, `reorder` | The advisor's methodology editor |
| `POST` | `/chat` | `{name, household_type}` to start; `{conversation_id, message}` to continue | Legacy free-form discovery (kept for the seeded demo families) |
| `POST` | `/analyze-values` | `{conversation_id}` | Structured values profile (`values, financial_priorities, life_goals, family_goals, legacy_goals, philanthropy, emotional_cues, money_script`) |
| `POST` | `/generate-purpose` | `{user_id}` | Wealth Purpose Statement (versioned) |
| `POST` | `/calculate-score` | `{user_id, portrait}` | `{overall, categories{cash_flow, investment, estate, philanthropy, risk}, themes, weighting_rationale}`; also stores advisor insights |
| `GET` | `/client-dashboard` | `?user_id=` | User, values, purpose, latest score |
| `GET` | `/advisor/clients` | | Book of clients with status and score |
| `GET` | `/advisor/clients/{id}` | | Dashboard + AI insights + transcript + notes |
| `POST` | `/advisor/clients/{id}/notes` | `{body}` | New note |
| `GET` | `/health` | | `{ok, demo_mode, model}` |

Each category returns `score` (0–100), `explanation`, `recommendations`, and its `weight` in the overall score.

## 5. Deployment

### Beta deployment checklist

**Railway (backend)** — set before the first deploy:

| Variable | Value |
|---|---|
| `APP_ENV` | `production` (Secure cookies; startup refuses to run misconfigured) |
| `OPENROUTER_API_KEY` | your key |
| `OPENROUTER_MODEL` | `openai/gpt-5.6-luna` |
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ADMIN_PASSWORD` | long random passphrase for Mimi (methodology editor, beta admin) |
| `ADVISOR_PASSWORD` | optional second, lower-privilege password |
| `DATABASE_URL` | injected by the Postgres plugin |
| `CORS_ORIGINS` | `https://<your-app>.vercel.app` |
| `DEMO_MODE` / `ALLOW_DEMO_IN_PRODUCTION` | **unset** for a real beta |

**Vercel (frontend)** — set before the first build (rewrites are baked in at build time):

| Variable | Value |
|---|---|
| `API_URL` | `https://<your-api>.up.railway.app` |
| `NEXT_PUBLIC_API_URL` | **unset** |

**Before inviting anyone**

1. `GET https://<api>/health` → `{"ok": true, "demo_mode": false, "app_env": "production", "model": "..."}`.
2. `/login` with the admin password → `/admin/clients` shows the green **Live model** banner (amber = demo; stop).
3. Run one real discovery yourself, share it, confirm the advisor view shows it and that an unshared second session shows only a name.
4. Delete your test client from `/admin/clients`.
5. Switch on Postgres backups in Railway.
6. Send each beta participant the `/discover` URL only; never resume links.

### Rotating secrets

- **`SECRET_KEY`**: set the new value in Railway and redeploy. **Every staff member is signed out immediately** (all existing
  staff cookies become invalid); client sessions are unaffected because they use database tokens, not the key.
- **`ADMIN_PASSWORD` / `ADVISOR_PASSWORD`**: set the new value and redeploy. Existing staff cookies stay valid until they expire
  (12 h) — rotate `SECRET_KEY` at the same time to end them at once.
- **A client's resume link**: `/admin/clients` → **Reset link**. Every existing link and signed-in device for that client stops working;
  hand the client the new link shown once on screen.
- **Rate limits**: 10 sign-in attempts and 30 resume-link attempts per address per 15 minutes (in-process; counters reset on restart).

### Hosts

**Backend → Railway**
1. New project from the repo, root directory `backend`.
2. Add the PostgreSQL plugin; Railway injects `DATABASE_URL`.
3. Set `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `APP_ENV=production`, `SECRET_KEY`, `ADMIN_PASSWORD`, and
   `CORS_ORIGINS=https://<your-app>.vercel.app`.
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

**Frontend → Vercel**
1. Import the repo, root directory `frontend` (framework auto-detected).
2. Set `API_URL=https://<your-api>.up.railway.app` (not `NEXT_PUBLIC_API_URL`): the frontend proxies `/api/*` to it.
   Next.js bakes rewrites in at build time, so set it before the first build and redeploy if it changes.

## 6. Two-minute demo script

1. Open `/` → **Begin your discovery** → enter a name and choose *A family*.
2. Work through the modules one question at a time (Love, Play, Work, Service, Alignment, Community, Evolution). Short answers get one follow-up; each module ends with **What we're hearing** to confirm or correct.
   **Save & continue later** pauses; the page resumes on return.
3. On the **Review** step ("Here's what Aligned AI understood about you") mark each insight Accurate / Partly / Edit /
   Clarify, open **Why?** to see the exact words behind it, then **Create my draft statement** → the nine-section
   draft (labelled DRAFT) → **Download PDF**.
4. **Measure my alignment** → adjust a few sliders → **Calculate** → the dashboard animates the score.
5. Click **Advisor view** → show AI insights, the values profile, and the recommended conversation.
   Then open **Sarah Johnson** from *All families* as the fully worked example.

## Notes for production

- Per-advisor accounts and data scoping (the beta has one shared advisor password and one admin password).
- Durable rate-limit and QA counters (in-process today; they reset on restart and are per backend instance).
- Portrait inputs are self-reported. A next step is custodial and aggregation data feeds.
- Review AI prompt wording and disclosures with compliance before client use.
