# SafeSpace Pro

SafeSpace Pro is a production-structured MVP for anonymous workplace harassment reporting built with **FastAPI + Streamlit + SQLite/PostgreSQL + scikit-learn**.

It includes:
- secure complaint submission
- one-time access code for anonymous follow-up
- encrypted complaint text and identity storage
- ML-assisted harassment category classification
- severity scoring
- HR/legal complaint queue and threaded replies
- analytics dashboard
- local, Docker, Vercel-backend, and free-hosting friendly setup

---

## 1) Architecture at a glance

### Backend
FastAPI handles API requests, validation, ticket creation, ML categorization, encryption, database operations, and admin endpoints.

### Frontend
Streamlit provides three main flows:
- anonymous complaint submission
- reporter ticket lookup and follow-up
- HR/admin dashboard with analytics and replies

### Data model
Two main tables:
- `complaints`: one row per complaint/ticket
- `complaint_messages`: threaded conversation between reporter and admin

### Security model
- complaint text and optional identity are encrypted with **Fernet**
- reporter gets a `ticket_id` and a one-time `access_code`
- only the **hash** of the access code is stored
- admin endpoints are protected by `X-Admin-Token`

---

## 2) Folder-by-folder explanation

```text
safespace_pro/
├── api/
│   └── index.py                  # Vercel entrypoint exposing the FastAPI ASGI app
├── backend/
│   ├── api/routes.py             # All API endpoints
│   ├── core/config.py            # Environment/config loading
│   ├── core/security.py          # Fernet encryption, access-code hashing, ticket generation
│   ├── db/base.py                # SQLAlchemy declarative base
│   ├── db/models.py              # Database tables / ORM models
│   ├── db/session.py             # SQLAlchemy engine and session factory
│   ├── repositories.py           # Business logic + DB reads/writes + analytics builders
│   ├── schemas.py                # Pydantic request/response models
│   ├── services/classifier.py    # Loads and runs the text classifier + severity logic
│   ├── model_artifacts/          # Saved ML model file
│   └── main.py                   # FastAPI app bootstrap
├── frontend/
│   ├── app.py                    # Streamlit UI
│   └── client.py                 # Requests-based API client used by Streamlit
├── scripts/
│   └── train_model.py            # Trains and saves the scikit-learn model artifact
├── tests/
│   └── test_api.py               # Integration-style API tests for main complaint flow
├── .streamlit/config.toml        # Streamlit runtime config
├── .env.example                  # Environment variables template
├── docker-compose.yml            # Run frontend + backend together locally via Docker
├── Dockerfile.backend            # Container for FastAPI
├── Dockerfile.frontend           # Container for Streamlit
├── render.yaml                   # Example Render blueprint
├── vercel.json                   # Vercel routing for backend deployment
├── requirements.txt              # Python dependencies
└── README.md                     # This document
```

---

## 3) Why each core technology is used

### FastAPI
Used for the backend because it gives:
- strong validation with Pydantic
- async-ready API framework
- automatic docs at `/docs`
- clean deployment story on Python-friendly hosts

### Streamlit
Used for the frontend because:
- it is fast to build forms and dashboards
- ideal for internal tools / admin dashboards / hackathon demos
- easy deployment on Streamlit Community Cloud

### SQLAlchemy
Used because it makes switching from SQLite (local demo) to PostgreSQL (deployment) much easier.

### SQLite + PostgreSQL
- **SQLite** is perfect for local development and fast demos.
- **PostgreSQL** is better for cloud deployment because many free hosts have ephemeral filesystems.

### Fernet encryption
Used to encrypt sensitive fields before they hit the database so raw complaint text and identity are not stored in plain text.

### scikit-learn
Used for a lightweight ML classifier that predicts complaint category:
- verbal harassment
- physical harassment
- digital harassment
- other

This is small, easy to understand, and deploys more easily than a transformer for an MVP.

---

## 4) Local run

### Step A — create a virtual environment

```bash
python3 -m venv .venv
```

#### Windows PowerShell
```powershell
.\.venv\Scripts\Activate.ps1
```

#### Linux / macOS / WSL
```bash
source .venv/bin/activate
```

### Step B — install dependencies

```bash
pip install -r requirements.txt
```

### Step C — train the demo ML model

```bash
python scripts/train_model.py
```

### Step D — create environment file

```bash
cp .env.example .env
```

Update at least:
- `ADMIN_TOKEN`
- `FERNET_KEY`

Generate a Fernet key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Step E — run backend

```bash
uvicorn backend.main:app --reload --port 8000
```

### Step F — run frontend

```bash
streamlit run frontend/app.py
```

Backend docs:
- `http://127.0.0.1:8000/docs`

Frontend:
- `http://127.0.0.1:8501`

---

## 5) Docker run

```bash
docker compose up --build
```

This starts:
- backend on `http://localhost:8000`
- frontend on `http://localhost:8501`

---

## 6) API summary

### Public endpoints
- `GET /api/v1/health`
- `POST /api/v1/complaints`
- `POST /api/v1/complaints/{ticket_id}/lookup`
- `POST /api/v1/complaints/{ticket_id}/messages`

### Admin endpoints
Requires header:
- `X-Admin-Token: <your-token>`

Endpoints:
- `GET /api/v1/admin/complaints`
- `GET /api/v1/admin/complaints/{ticket_id}`
- `POST /api/v1/admin/complaints/{ticket_id}/messages`
- `PATCH /api/v1/admin/complaints/{ticket_id}/status`
- `GET /api/v1/admin/analytics`

---

## 7) Common errors and how this project handles them

### Error: `sqlite3.OperationalError: no such table`
Cause: DB tables were not created.
Fix in this project: tables are auto-created on FastAPI startup.

### Error: Streamlit cannot reach backend
Cause: backend not running or wrong `BACKEND_BASE_URL`.
Fix: set `BACKEND_BASE_URL` correctly in environment and verify via sidebar health check.

### Error: encrypted text cannot be decrypted after redeploy
Cause: changed or missing `FERNET_KEY`.
Fix: keep the same `FERNET_KEY` across deployments.

### Error: complaint data disappears on free cloud redeploy
Cause: using SQLite on an ephemeral filesystem.
Fix: for cloud deployment use PostgreSQL instead of local SQLite.

### Error: invalid admin token
Cause: wrong or missing `X-Admin-Token`.
Fix: send the exact `ADMIN_TOKEN` set in the environment.

### Error: Vercel works for API but database resets
Cause: Vercel serverless filesystem is not suitable for persistent SQLite storage.
Fix: use managed PostgreSQL.

### Error: access code lost
Cause: code is intentionally shown once.
Fix: save it immediately after complaint submission. The backend stores only its hash.

### Error: model file missing
Cause: `backend/model_artifacts/harassment_classifier.joblib` not present.
Fix: run:

```bash
python scripts/train_model.py
```

---

## 8) Deployment guidance

### Best practical free combo
#### Option A — easiest real-world free deployment
- **Frontend:** Streamlit Community Cloud
- **Backend:** Render Free web service or Koyeb free web service
- **Database:** Render Postgres free / Koyeb free Postgres / Supabase Postgres

### Vercel
Use Vercel for the **FastAPI backend only**, not the Streamlit frontend.

Important notes:
- Vercel can run FastAPI as a Python function.
- Do **not** rely on SQLite there.
- Set these environment variables in Vercel:
  - `DATABASE_URL` → managed PostgreSQL
  - `ADMIN_TOKEN`
  - `FERNET_KEY`
  - `CORS_ORIGINS`

### Streamlit Community Cloud
Deploy `frontend/app.py` from GitHub.
Set secret/environment:
- `BACKEND_BASE_URL=https://your-backend-url`

### Render
You can deploy both the frontend and backend as free web services.
Important limitation: free web services spin down after 15 minutes idle, local filesystem is ephemeral, and free Postgres databases expire 30 days after creation. Use PostgreSQL, not SQLite, for deployed data.

### Netlify
Netlify is **not a good host for this full Python app**. You can use Netlify for a static landing page or frontend assets, but not for running this Streamlit + FastAPI server architecture directly.

---

## 9) Recommended next improvements if you want to push this toward production

- replace shared admin token with proper admin login + RBAC
- add audit logs
- add email notifications / webhook notifications
- replace demo classifier with a curated dataset and better evaluation
- add file attachments stored in object storage
- add rate limiting and abuse protection
- add background moderation and escalation workflows
- add Alembic migrations instead of startup table creation
- add pytest coverage + CI pipeline
- add separate React frontend if you want public product-grade UX

---

## 10) How to think like the builder of this app

This project follows a simple product-engineering pattern:

1. **Identify the minimum trusted workflow**
   - report incident
   - track ticket
   - admin review
   - secure follow-up

2. **Separate responsibilities**
   - frontend handles UI only
   - backend handles rules, security, storage, and ML
   - DB stores state

3. **Use cheap local defaults but cloud-safe abstractions**
   - SQLite locally
   - PostgreSQL in the cloud

4. **Protect sensitive data early**
   - encrypt before save, not later
   - never store the raw access code

5. **Design for upgrade paths**
   - rule-based severity can later become a real model
   - token auth can later become full auth
   - Streamlit can later be replaced with React without changing the backend API much

That is the core thinking pattern you should reuse for your own apps.
