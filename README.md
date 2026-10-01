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

The AI supports the advisor; it never gives the client financial advice. The alignment score is
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
| `ANTHROPIC_API_KEY` | empty | Claude credentials. If empty, the app runs in **demo mode** with a deterministic stand-in. |
| `CLAUDE_MODEL` | `claude-opus-5-5` | Model used for every AI step |
| `DEMO_MODE` | `false` | Force demo mode even with a key (offline rehearsals) |
| `DATABASE_URL` | SQLite `backend/aligned.db` | e.g. `postgresql+psycopg://user:pass@localhost:5432/aligned` (`postgres://` URLs are accepted) |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated frontend origins |

**frontend/.env.local**

| Variable | Default |
|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` |

If a Claude call fails or is declined mid-demo, that step falls back to the demo engine and the flow
continues. `GET /health` reports which mode is active.

## 3. Database setup (PostgreSQL)

```bash
createdb aligned
# either let the API create tables on startup, or apply the reference schema:
psql -d aligned -f backend/schema.sql
```

Tables: `users`, `conversations`, `values`, `purpose_statements`, `alignment_scores`, `advisor_notes`.
To reseed with SQLite, delete `backend/aligned.db` and restart.

## 4. API

Interactive docs are at `http://localhost:8000/docs`.

| Method | Path | Body / query | Returns |
|---|---|---|---|
| `POST` | `/chat` | `{name, household_type}` to start; `{conversation_id, message}` to continue | `{conversation_id, user_id, reply, stage, answered, ready, demo_mode}` |
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

**Backend → Railway**
1. New project from the repo, root directory `backend`.
2. Add the PostgreSQL plugin; Railway injects `DATABASE_URL`.
3. Set `ANTHROPIC_API_KEY` and `CORS_ORIGINS=https://<your-app>.vercel.app`.
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

**Frontend → Vercel**
1. Import the repo, root directory `frontend` (framework auto-detected).
2. Set `NEXT_PUBLIC_API_URL=https://<your-api>.up.railway.app`.

## 6. Two-minute demo script

1. Open `/` → **Begin your discovery** → enter a name and choose *A family*.
2. Answer five questions (one or two sentences each is enough). Mention children, education, climate, and
   how money was talked about growing up.
3. Click **Create my statement** → walk through the Wealth Purpose Statement → **Download PDF**.
4. **Measure my alignment** → adjust a few sliders → **Calculate** → the dashboard animates the score.
5. Click **Advisor view** → show AI insights, the values profile, and the recommended conversation.
   Then open **Sarah Johnson** from *All families* as the fully worked example.

## Notes for production

- Add authentication and per-advisor data scoping (the prototype has an open advisor view).
- Portrait inputs are self-reported. A next step is custodial and aggregation data feeds.
- Review AI prompt wording and disclosures with compliance before client use.
