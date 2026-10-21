# SafeSpace Pro setup and deployment

This guide describes the checked-in implementation and the limitations that affect deployment. Run repository commands from the directory containing `requirements.txt`, `render.yaml`, and this document. The Render Blueprint in this repository is configured for a non-production demo; it does not make the application suitable for real workplace reports.

## Prerequisites and repository layout

- Python 3.11.11 is selected by [`runtime.txt`](runtime.txt). Use Python 3.11 for closest parity; the source also targets modern Python 3.11+.
- `pip` and, optionally, Docker with Docker Compose v2.
- A browser for Streamlit and FastAPI's OpenAPI page.
- A GitHub account and Render account only for manual hosted deployment.

Important paths:

| Path | Purpose |
| --- | --- |
| `backend/main.py` | FastAPI app, startup checks, database table creation |
| `backend/api/routes.py` | Health, reporter, and admin routes |
| `backend/core/config.py` | Environment settings and production validation |
| `backend/core/security.py` | Fernet encryption, access-code hashing, ticket generation |
| `backend/db/` | SQLAlchemy base, entities, and engine/session |
| `backend/repositories.py` | Complaint writes, reads, follow-up, analytics |
| `backend/services/classifier.py` | Required saved model and severity heuristic |
| `backend/model_artifacts/harassment_classifier.joblib` | Tracked model loaded on startup |
| `frontend/` | Streamlit interface and HTTP client |
| `tests/test_api.py` | Local API/security tests using a temporary SQLite database |
| `scripts/train_model.py` | Explicit model retraining, not part of ordinary deployment |

The application expects the repository root as the working directory. Relative paths such as `MODEL_PATH` and the default SQLite file are resolved from that directory.

## Local setup

### 1. Clone and enter the repository

```bash
git clone https://github.com/SiddharthSoumya/safespace.git
cd safespace
```

### 2. Create and activate a virtual environment

Linux:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

macOS (if `python3.11` is installed):

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use the Python executable directly (`.\.venv\Scripts\python.exe`) rather than changing machine-wide execution policy.

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The model artifact was serialized using scikit-learn 1.8.0, so that version is pinned in `requirements.txt`. Starlette is constrained below 1.0 with HTTPX installed because Starlette 1.x changed the test-client dependency interface; these constraints are verified by this repository's test suite.

### 4. Configure secrets and local database

Create `.env` only if it does not already exist. Do not overwrite an existing local environment file:

```bash
if [ ! -e .env ]; then cp .env.example .env; fi
```

Windows PowerShell:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Edit `.env` locally (it is ignored by Git):

```dotenv
APP_ENV=development
DATABASE_URL=sqlite:///./data/safespace.db
ADMIN_TOKEN=<a-unique-long-random-token>
FERNET_KEY=<generated-fernet-key>
BACKEND_BASE_URL=http://127.0.0.1:8000
CORS_ORIGINS=http://localhost:8501,http://127.0.0.1:8501
```

Generate a Fernet key and a separate strong admin token; paste the output only into your local `.env` or a secrets manager:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

`BACKEND_BASE_URL` is consumed by the Streamlit HTTP client. `CORS_ORIGINS` controls API browser CORS; the Streamlit client itself makes server-to-server requests, so cross-origin access is not needed for the ordinary UI workflow. SQLite is suitable for local testing only. The local development key file fallback is intended only for development; use a stable explicit `FERNET_KEY` even locally if you need to preserve locally stored reports.

### 5. Verify the classifier

The committed file `backend/model_artifacts/harassment_classifier.joblib` is required and is loaded at FastAPI startup. Verify it is present:

```bash
python -c "from pathlib import Path; p=Path('backend/model_artifacts/harassment_classifier.joblib'); print(p, p.stat().st_size, 'bytes')"
```

If deliberately retraining, first install the pinned dependencies, then run:

```bash
python scripts/train_model.py
```

This overwrites the tracked model artifact. Review the resulting model change and verify its predictions/tests before committing. Training is not part of Render builds.

### 6. Start the backend and UI

Terminal 1:

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2, from the repository root with the same virtual environment:

```bash
streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501
```

Browse to `http://127.0.0.1:8501`. The API startup loads the model and calls SQLAlchemy `create_all()`; local SQLite is created under `data/`. Check:

```bash
curl --fail http://127.0.0.1:8000/api/v1/health
```

The health endpoint executes a database probe. Interactive API docs are at `http://127.0.0.1:8000/docs`; the OpenAPI JSON is at `http://127.0.0.1:8000/openapi.json`.

### 7. Run tests

```bash
python -m pytest -q
```

Tests set their test key before importing the app and use a dedicated temporary SQLite database outside the project. They do not delete or modify your local `data/safespace.db`.

### 8. Optional local Docker Compose

Create `.env` and configure the key/token as above, then run from the repository root:

```bash
docker compose up --build
```

The backend is at `http://localhost:8000` and Streamlit at `http://localhost:8501`. Compose mounts `./data` into the backend container so local SQLite and a locally generated development key file persist across container recreation. Do not use that mount as a cloud database strategy. Stop with `Ctrl+C`; remove containers with `docker compose down` (this does not delete `./data`).

The backend receives `.env`; the frontend receives only `BACKEND_BASE_URL`, not the backend's admin/encryption secrets. The Docker build context excludes `.env`, local database/key files, caches, and Git metadata via `.dockerignore`; keep that protection in place if adding local runtime files.

## Configuration reference

| Variable | Used by | Default / requirement |
| --- | --- | --- |
| `APP_ENV` | Backend | `development`; set to `production` on Render to enable strict secret/database checks. |
| `DATABASE_URL` | Backend | `sqlite:///./data/safespace.db`; use PostgreSQL for hosted service. `postgres://` and `postgresql://` are normalized to the psycopg 3 SQLAlchemy dialect. |
| `ADMIN_TOKEN` | Backend | Development default is intentionally unsafe. Production requires at least 32 characters; generate a random token and keep it secret. |
| `FERNET_KEY` | Backend | Optional in development (a local key file is created if absent); mandatory and validated in production. It must remain unchanged for existing records. |
| `FERNET_KEY_FILE` | Backend | `data/fernet.key`; local-only fallback when `FERNET_KEY` is unset. |
| `MODEL_PATH` | Backend | `backend/model_artifacts/harassment_classifier.joblib`; required at startup. |
| `TICKET_PREFIX` | Backend | `SAFE`. |
| `CORS_ORIGINS` | Backend | Local Streamlit origins by default; comma-separated exact origins. Empty disables cross-origin requests. |
| `BACKEND_BASE_URL` | Streamlit frontend | `http://127.0.0.1:8000`; Render supplies the API service host. If no scheme is supplied, the client assumes HTTPS. HTTP requests time out after 90 seconds to tolerate a free-service cold start. |

Production startup fails if `APP_ENV=production` and the admin token, valid Fernet key, or PostgreSQL URL is missing/invalid. Keep secrets out of `render.yaml`, `.env.example`, Git commits, screenshots, support tickets, and logs.

## Render deployment (manual; no deployment performed)

### Important suitability boundary

The checked-in Blueprint uses free Render web services and a free Render Postgres database to make a demo deploy possible. Render's current [free plan documentation](https://render.com/docs/free) states that free web services spin down after 15 minutes without inbound traffic, can take about a minute to spin back up, use ephemeral filesystems, and that free Postgres expires 30 days after creation and has no backups. Free services are not appropriate for storing real workplace reports. Use fictional data only on this Blueprint. Select a currently available paid Postgres plan and review data-handling/legal/security requirements before any real-data pilot; paid infrastructure alone does not make this application production-ready.

The Blueprint uses the Render service runtime (`runtime: python`), the repository root as each service's root directory, and `runtime.txt` for the Python version. Its exact commands are:

```text
Backend build: pip install -r requirements.txt
Backend start: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
Frontend build: pip install -r requirements.txt
Frontend start: streamlit run frontend/app.py --server.address 0.0.0.0 --server.port $PORT
```

The source `render.yaml` has three resources in the same Oregon region:

1. `safespace-db` PostgreSQL, currently `plan: free` (demo-only).
2. `safespace-api` Python web service with `/api/v1/health` health check.
3. `safespace-ui` Python web service. Its `BACKEND_BASE_URL` is set from the API service's generated `host`; the frontend HTTP client adds `https://` if needed.

Render Blueprints support `fromDatabase` for the PostgreSQL connection string, `fromService` for the backend host, and `sync: false` for secrets entered through the dashboard. See the current [Blueprint specification](https://render.com/docs/blueprint-spec) and [Postgres connection guide](https://render.com/docs/postgresql-creating-connecting). The database and both services use the same region so the backend can use the database's internal connection string.

### Deploy with a Blueprint

1. Review the branch and diff locally. Run the tests below and ensure no `.env`, database, Fernet key, or other secret is staged.
2. Push the prepared branch to GitHub yourself. This assistant has not pushed code or changed repository settings.
3. In Render, choose **New + → Blueprint** and connect the GitHub repository and branch containing `render.yaml`. Blueprint is preferred over manually creating three resources because it keeps the two services, database reference, health check, and generated service-to-service URL together as code.
4. Review all resources before confirming. The Blueprint currently requests a free database. For any persistent pilot, change the database to a currently offered paid plan in the Blueprint/dashboard before creating it; check price, storage, backups, retention, and region in Render at that time.
5. Confirm the database and API/UI service regions match (currently Oregon). The `DATABASE_URL` reference uses the managed database connection string; Render's internal connection is preferred for same-region services.
6. When Render prompts for Blueprint values, enter:
   - `ADMIN_TOKEN`: generate `secrets.token_urlsafe(32)` locally or in a trusted secret manager. Never use the development default.
   - `FERNET_KEY`: generate with `Fernet.generate_key()` using the same Fernet library. Store a protected offline backup and preserve this exact key through rebuilds, restarts, and restores.
   - `APP_ENV` is fixed as `production` in the Blueprint.
   - `DATABASE_URL` is a Render database reference, not a manually copied public URL.
   - `CORS_ORIGINS` is empty because Streamlit calls the backend server-to-server. Add only explicit browser origins if a separate browser client is intentionally introduced.
   - `BACKEND_BASE_URL` is a `fromService` reference. Do not replace it with a guessed hostname.
7. Verify Render's service **Root Directory** is blank/repository root. Do not set it to `backend/` or `frontend/`: both services need root-level `requirements.txt` and package paths, and the API also needs the tracked model artifact.
8. Render resolves the managed database reference before starting the API; the UI's service reference supplies the generated API host without hardcoding a URL. Wait for the database to become available, then confirm the API and UI deploy.
9. Inspect build logs for dependency installation and service logs for startup. The API startup must load the model and create the initial schema; health checks should pass only after its PostgreSQL probe succeeds. The UI should bind to `$PORT` and pass its health check.
10. Test `/api/v1/health` and `/docs` at the API's generated URL. Then test the UI's **Check API Health** button.
11. Submit a fictional test report only. Save the returned ticket ID and access code in a safe temporary location, verify lookup and a follow-up, then check that a test admin token can see/reply/update status. Do not put actual employee data in a demo project.
12. When satisfied, keep auto-deploys enabled for the selected branch or deploy manually from Render's **Deploys** page. Render deploys on commits by default when a Git provider is connected. Read build/runtime logs after every deployment.

### Create services manually instead

Use **New + → Web Service** twice and **New + → PostgreSQL** if you do not want a Blueprint. Both web services must use root directory `.`, Python runtime, and the exact build/start commands above. Configure the API with `APP_ENV=production`, `DATABASE_URL` from the same-region database's internal URL, the generated long `ADMIN_TOKEN`, and stable `FERNET_KEY`; set `CORS_ORIGINS` blank unless there is a separate web origin. Configure the UI with `BACKEND_BASE_URL=https://<the-API-host>` (use the actual Render service URL, not a placeholder). Set the API health-check path to `/api/v1/health`. Choose service plans deliberately; do not assume a free database is persistent or backed up.

### Data, secrets, operation, and recovery

- **Persistence and backup:** Hosted complaint data belongs in managed PostgreSQL, never SQLite or the web-service filesystem. A free database expires after 30 days and has no backups. Render documents point-in-time recovery and on-demand logical exports for paid Postgres; confirm current retention and recovery objectives in the dashboard and Render docs. Perform and test exports/restores before any meaningful data is entered.
- **Schema:** the app currently runs SQLAlchemy `create_all()` at startup. It creates missing tables but does not perform schema migrations or safely evolve existing production structures. There is no migration command in this repository. This is a blocker for production use; add and test a migration system and a controlled pre-deploy migration process before production.
- **Fernet key:** never regenerate it after storing encrypted rows. Replacing it makes existing complaint text, identities, and messages undecryptable. There is no key versioning or re-encryption utility. Safe rotation needs a separately designed, tested, backed-up re-encryption migration; do not simply change the environment variable.
- **Admin token:** changing `ADMIN_TOKEN` invalidates the previous token immediately after the new deployment. Update the protected secret and coordinate the admin/operator transition. This is a single shared token, not per-user authentication or role-based access.
- **Previously issued access codes:** new access codes have 128 bits of randomness. Older deployments generated shorter codes; they remain valid against their existing stored hashes for compatibility and have less entropy. If migrating old records, plan a controlled access-code replacement strategy rather than assuming all stored credentials have the new strength.
- **Environment updates:** use Render's protected environment-variable editor, do not paste secrets into Git or public logs, and trigger a redeploy/restart when Render requests it. Coordinate changes across service variables and the operator holding the admin token; changing only the API token can temporarily lock out dashboard users.
- **Deploy rollback:** a code rollback does not roll back database writes. Render documents rollback availability for recent deploys; verify the currently available rollback window in the dashboard. Restore data from a verified database backup separately. Do not run destructive schema downgrades.
- **Idle/cold starts and sizing:** free web services currently spin down after 15 minutes idle and may take about a minute to wake. Render's Blueprint docs list the free compute plan as 0.1 CPU and 512 MB RAM; that can constrain simultaneous Streamlit, pandas, scikit-learn, and API work. The frontend or API may cold-start on the first request. Free instance-hour quotas, resource limits, database expiration, and pricing can change; re-check Render's current docs before deployment.
- **Monitoring:** inspect the build log for dependency/model artifacts and the runtime log for missing settings, database connection failures, model load errors, and health-check failures. Avoid sending report text, access codes, tokens, or Fernet keys to logs or support systems.
- **Privacy:** the app does not establish full anonymity. Render/network operators may have request metadata; ticket IDs and request paths can appear in platform access logs. The app has no in-app rate limiter, audit trail, privacy notice, retention/deletion workflow, account-based admin identity, or incident response procedure.

### Render troubleshooting

| Symptom | Likely cause | Action |
| --- | --- | --- |
| Build cannot find `requirements.txt` or `backend` | Incorrect service root directory | Set root directory to repository root (`.`/blank) and redeploy. |
| API fails before listening | Missing `ADMIN_TOKEN`, invalid/missing `FERNET_KEY`, or `APP_ENV` set to production with SQLite | Set strong dashboard secrets and confirm PostgreSQL is referenced; inspect API logs without copying secret values. |
| API health check fails | Backend startup/schema/model failure or database unavailable | Read runtime logs, verify model artifact is tracked and the database is available in the same region, then retry deploy. |
| Classifier `FileNotFoundError` | Model omitted from build context or incorrect root directory | Include `backend/model_artifacts/harassment_classifier.joblib`; keep root at repository root. |
| Model warning/error on load | scikit-learn version mismatch or corrupt artifact | Keep `scikit-learn==1.8.0`; retrain only using pinned requirements and test before deploying. |
| UI shows connection error | Wrong/missing backend service URL or API cold start | Check generated backend host in the UI environment; client accepts a host and adds HTTPS. Check API service health/logs. |
| API works locally but ticket decrypt fails after restart | Fernet key changed or was generated only on ephemeral disk | Restore the exact original Fernet key from protected backup; do not generate a replacement for existing rows. |
| Reports disappear or database becomes unavailable | SQLite used in a web service, or free Postgres expired | Configure managed Postgres and select a plan with required persistence/backup and retention. |
| `401` from admin routes | Wrong/missing `X-Admin-Token` | Use the exact current `ADMIN_TOKEN` in the protected admin UI/environment. Rotate only with a coordinated change. |
| Tests fail to collect `TestClient` | Starlette/HTTPX compatibility drift | Install from `requirements.txt` in a clean virtual environment; retain its Starlette and HTTPX constraints. |

### Deployment acceptance checklist

- [ ] Secrets are entered only in Render's secret environment settings and are backed up securely.
- [ ] All services and PostgreSQL share the selected region; `DATABASE_URL` is the internal managed database reference.
- [ ] The database plan's expiration, backups, restore procedure, storage, and cost are acceptable.
- [ ] Both services build from repository root and use the specified `$PORT` commands.
- [ ] API model load and PostgreSQL health check succeed; `/docs` is reachable.
- [ ] The Streamlit health check reaches the generated API service.
- [ ] A fictional report can be submitted, looked up, and followed up with; an admin can review it with the configured token.
- [ ] Test credentials and test report are not mistaken for production identity/authorization controls.
- [ ] No confidential workplace report is entered until the production blockers below are resolved.

## Production blockers and future work

Passing tests and deploying the demo does not make this a production system. At minimum, a real deployment requires managed admin identity and authorization, rate limiting and abuse controls, audit events without sensitive payloads, schema migrations, tested backup/restore and key-rotation procedures, an explicit data-retention/deletion policy, operational monitoring, and a formal security/privacy review. The current training data and severity heuristic are not clinically, legally, or operationally validated.

## Related documents

- [Project overview](README.md)
- [Architecture, data handling, and limitations](ARCHITECTURE.md)
