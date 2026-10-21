# SafeSpace Pro

SafeSpace Pro is a small FastAPI and Streamlit application for submitting workplace-harassment reports, retrieving a report with a ticket ID and access code, and reviewing reports through a shared-token administrator interface.

## Features present in the code

- Complaint submission with required text, optional identity and department, and automatic or manual category selection.
- Ticket-based reporter lookup and encrypted follow-up messages.
- Optional identity, complaint text, and conversation messages encrypted with Fernet before database persistence.
- Hashed reporter access codes and `X-Admin-Token` protected administration endpoints.
- scikit-learn category prediction and rule-based severity labels.
- Administrative queue, status updates, replies, and aggregate counts.

These are starter-app behaviors, not a claim of anonymity, compliance, or production readiness. The classifier is trained on a small illustrative dataset; requests are not rate limited; administration uses one shared static token; and database tables are created with `create_all()` rather than migrations. Do not use it for real sensitive reports until the blockers in [SETUP.md](SETUP.md) and [ARCHITECTURE.md](ARCHITECTURE.md) have been addressed.

## Stack and architecture

- Python 3.11.11 (see [`runtime.txt`](runtime.txt))
- FastAPI, Pydantic, SQLAlchemy 2
- Streamlit and Requests
- SQLite for local development; PostgreSQL through Render for hosted deployments
- Fernet encryption and a versioned scikit-learn artifact

The Streamlit process calls the separately hosted FastAPI service over HTTP. The API stores complaint and message rows in SQLAlchemy models. The Render Blueprint defines two Python web services and a PostgreSQL database. See the [architecture document](ARCHITECTURE.md).

## Repository map

```text
backend/          FastAPI routes, config, cryptography, persistence, classifier
frontend/         Streamlit UI and HTTP API client
tests/            API and security-focused tests
scripts/          Model training utility
backend/model_artifacts/
                  Tracked classifier artifact needed at startup
render.yaml       Render Blueprint for API, UI, and PostgreSQL
Dockerfile.*      Optional local container builds
docker-compose.yml
                  Local API + UI with SQLite
```

## Quick start

Run commands from the repository root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
if [ ! -e .env ]; then cp .env.example .env; fi
```

Set a unique local `ADMIN_TOKEN` and generate `FERNET_KEY` with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

The tracked model is loaded during API startup; retrain only when intentionally replacing it:

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
# In a second terminal:
streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501
```

Open `http://127.0.0.1:8501`, check the API at `http://127.0.0.1:8000/api/v1/health`, and view OpenAPI at `http://127.0.0.1:8000/docs`. Run tests with `python -m pytest -q`.

For Windows PowerShell, Docker Compose, configuration details, troubleshooting, and the complete manual Render walkthrough, see [SETUP.md](SETUP.md).

## API

The OpenAPI document is available at `/openapi.json` and interactive docs at `/docs`. Current route prefixes are `/api/v1`; administrator routes require `X-Admin-Token`.

## Deployment

`render.yaml` is a **demo-oriented** Blueprint. Its free PostgreSQL database expires after 30 days and does not provide backups; free web services spin down when idle. Select an appropriate paid database plan before accepting any real confidential data. Even with paid infrastructure, the application needs production-grade identity/access management, abuse controls, schema migrations, operational monitoring, and security review before it can be considered fit for real workplace cases.

## License

This repository includes an [MIT License](LICENSE).
