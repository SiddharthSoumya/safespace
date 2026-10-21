from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

_TEST_DATA = tempfile.TemporaryDirectory(prefix="safespace-tests-")
_TEST_DATABASE = Path(_TEST_DATA.name) / "test.db"
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DATABASE}"
os.environ["FERNET_KEY"] = Fernet.generate_key().decode("utf-8")
os.environ["ADMIN_TOKEN"] = "test-admin-token"

from sqlalchemy import select

from backend.core.config import Settings
from backend.core import security
from backend.core.security import decrypt_text, encrypt_text, hash_access_code, verify_access_code_hash
from backend.db.base import Base
from backend.db.models import Complaint
from backend.db.session import SessionLocal, engine
from backend.main import app
from backend.services.classifier import classify_text, load_model


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    _TEST_DATA.cleanup()


def test_health_endpoint_checks_database(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_full_complaint_flow_and_encrypted_persistence(client: TestClient) -> None:
    text = "My manager kept sending abusive late-night messages on chat and insulting me in public."
    identity = "employee-123"
    create_response = client.post(
        "/api/v1/complaints",
        json={
            "text": text,
            "identity": identity,
            "department": "Engineering",
            "use_auto_classification": True,
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["ticket_id"].startswith("SAFE-")
    assert len(created["access_code"]) == 32

    with SessionLocal() as db:
        stored = db.scalar(select(Complaint).where(Complaint.ticket_id == created["ticket_id"]))
        assert stored is not None
        assert stored.encrypted_text != text
        assert stored.encrypted_identity != identity
        assert stored.access_code_hash == hash_access_code(created["access_code"])
        assert stored.access_code_hash != created["access_code"]

    lookup_response = client.post(
        f"/api/v1/complaints/{created['ticket_id']}/lookup",
        json={"access_code": created["access_code"]},
    )
    assert lookup_response.status_code == 200
    lookup = lookup_response.json()
    assert lookup["text"] == text
    assert lookup["identity"] == identity
    assert lookup["department"] == "Engineering"
    assert len(lookup["messages"]) == 1

    invalid_lookup = client.post(
        f"/api/v1/complaints/{created['ticket_id']}/lookup",
        json={"access_code": "not-the-code"},
    )
    assert invalid_lookup.status_code == 404

    follow_up_response = client.post(
        f"/api/v1/complaints/{created['ticket_id']}/messages",
        json={"access_code": created["access_code"], "text": "This has been happening for three weeks."},
    )
    assert follow_up_response.status_code == 200
    assert len(follow_up_response.json()["messages"]) == 2

    admin_reply_response = client.post(
        f"/api/v1/admin/complaints/{created['ticket_id']}/messages",
        json={"text": "We have started reviewing your report."},
        headers={"X-Admin-Token": "test-admin-token"},
    )
    assert admin_reply_response.status_code == 200
    replied = admin_reply_response.json()
    assert replied["status"] == "UNDER_REVIEW"
    assert any(message["sender_role"] == "admin" for message in replied["messages"])

    status_response = client.patch(
        f"/api/v1/admin/complaints/{created['ticket_id']}/status",
        json={"status": "RESOLVED"},
        headers={"X-Admin-Token": "test-admin-token"},
    )
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "RESOLVED"

    analytics_response = client.get(
        "/api/v1/admin/analytics",
        headers={"X-Admin-Token": "test-admin-token"},
    )
    assert analytics_response.status_code == 200
    assert analytics_response.json()["total_complaints"] == 1


@pytest.mark.parametrize("path", ["/api/v1/admin/complaints", "/api/v1/admin/analytics"])
def test_admin_routes_reject_missing_or_invalid_token(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 401
    assert client.get(path, headers={"X-Admin-Token": "wrong-token"}).status_code == 401


def test_invalid_submission_is_rejected(client: TestClient) -> None:
    response = client.post("/api/v1/complaints", json={"text": "short"})
    assert response.status_code == 422


def test_fernet_round_trip_and_invalid_ciphertext() -> None:
    encrypted = encrypt_text("sensitive message")
    assert encrypted is not None
    assert encrypted != "sensitive message"
    assert decrypt_text(encrypted) == "sensitive message"
    with pytest.raises(RuntimeError, match="FERNET_KEY"):
        decrypt_text("not-a-valid-fernet-token")


def test_access_code_hash_verification() -> None:
    access_code = "A" * 32
    encoded_hash = hash_access_code(access_code)
    assert verify_access_code_hash(encoded_hash, access_code)
    assert not verify_access_code_hash(encoded_hash, "B" * 32)


def test_local_fernet_key_is_private_and_stable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    key_path = tmp_path / "fernet.key"
    monkeypatch.setattr(security.settings, "fernet_key", None)
    monkeypatch.setattr(security.settings, "fernet_key_file", str(key_path))
    monkeypatch.setattr(security.settings, "app_env", "development")

    first_cipher = security._load_or_create_fernet()
    second_cipher = security._load_or_create_fernet()
    ciphertext = first_cipher.encrypt(b"persisted")
    assert second_cipher.decrypt(ciphertext) == b"persisted"
    if os.name == "posix":
        assert key_path.stat().st_mode & 0o777 == 0o600


def test_classifier_artifact_loads_and_predicts() -> None:
    assert load_model() is not None
    category, confidence = classify_text("I received unwanted direct messages and abusive emails online.")
    assert category == "digital harassment"
    assert 0 <= confidence <= 1


def test_production_configuration_rejects_missing_secrets() -> None:
    settings = Settings(
        app_env="production",
        admin_token="a" * 32,
        fernet_key="",
        database_url="postgresql://localhost/safespace",
        _env_file=None,
    )
    with pytest.raises(RuntimeError, match="FERNET_KEY"):
        settings.validate_runtime()


def test_production_configuration_rejects_invalid_fernet_key() -> None:
    settings = Settings(
        app_env="production",
        admin_token="a" * 32,
        fernet_key="not-a-valid-fernet-key",
        database_url="postgresql://localhost/safespace",
        _env_file=None,
    )
    with pytest.raises(RuntimeError, match="valid Fernet key"):
        settings.validate_runtime()


@pytest.mark.parametrize(
    ("database_url", "cors_origins", "message"),
    [
        ("sqlite:///./data/safespace.db", "", "PostgreSQL"),
        ("postgresql://localhost/safespace", "*", "wildcard"),
    ],
)
def test_production_configuration_rejects_unsafe_database_or_cors(
    database_url: str,
    cors_origins: str,
    message: str,
) -> None:
    settings = Settings(
        app_env="production",
        admin_token="a" * 32,
        fernet_key=Fernet.generate_key().decode("utf-8"),
        database_url=database_url,
        cors_origins=cors_origins,
        _env_file=None,
    )
    with pytest.raises(RuntimeError, match=message):
        settings.validate_runtime()
