from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

# Configure test settings before app import
os.environ["DATABASE_URL"] = "sqlite:///./data/test_safespace.db"
os.environ["FERNET_KEY"] = Fernet.generate_key().decode("utf-8")
os.environ["ADMIN_TOKEN"] = "test-admin-token"

from backend.db.base import Base
from backend.db.session import engine
from backend.main import app

client = TestClient(app)


def setup_module(module):
    Path("data").mkdir(exist_ok=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
    db_file = Path("data/test_safespace.db")
    if db_file.exists():
        db_file.unlink()


def test_full_complaint_flow():
    create_response = client.post(
        "/api/v1/complaints",
        json={
            "text": "My manager kept sending abusive late-night messages on chat and insulting me in public.",
            "identity": "employee-123",
            "department": "Engineering",
            "use_auto_classification": True,
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["ticket_id"].startswith("SAFE-")
    assert created["access_code"]

    lookup_response = client.post(
        f"/api/v1/complaints/{created['ticket_id']}/lookup",
        json={"access_code": created["access_code"]},
    )
    assert lookup_response.status_code == 200
    lookup = lookup_response.json()
    assert lookup["department"] == "Engineering"
    assert len(lookup["messages"]) == 1

    follow_up_response = client.post(
        f"/api/v1/complaints/{created['ticket_id']}/messages",
        json={"access_code": created["access_code"], "text": "This has been happening for three weeks."},
    )
    assert follow_up_response.status_code == 200
    follow_up = follow_up_response.json()
    assert len(follow_up["messages"]) == 2

    admin_list_response = client.get(
        "/api/v1/admin/complaints",
        headers={"X-Admin-Token": "test-admin-token"},
    )
    assert admin_list_response.status_code == 200
    complaints = admin_list_response.json()
    assert len(complaints) == 1

    admin_reply_response = client.post(
        f"/api/v1/admin/complaints/{created['ticket_id']}/messages",
        json={"text": "We have started reviewing your report."},
        headers={"X-Admin-Token": "test-admin-token"},
    )
    assert admin_reply_response.status_code == 200
    replied = admin_reply_response.json()
    assert any(msg["sender_role"] == "admin" for msg in replied["messages"])

    analytics_response = client.get(
        "/api/v1/admin/analytics",
        headers={"X-Admin-Token": "test-admin-token"},
    )
    assert analytics_response.status_code == 200
    analytics = analytics_response.json()
    assert analytics["total_complaints"] == 1
