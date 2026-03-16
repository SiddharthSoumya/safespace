from __future__ import annotations

import os
from typing import Any

import requests

BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
API_BASE = f"{BACKEND_BASE_URL}/api/v1"
TIMEOUT = 20


class APIError(Exception):
    pass


def _handle(response: requests.Response) -> Any:
    try:
        payload = response.json()
    except ValueError as exc:
        raise APIError(f"Backend returned non-JSON response (status {response.status_code}).") from exc

    if response.ok:
        return payload

    detail = payload.get("detail", payload)
    raise APIError(str(detail))


def health_check() -> dict[str, Any]:
    response = requests.get(f"{API_BASE}/health", timeout=TIMEOUT)
    return _handle(response)


def submit_complaint(payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(f"{API_BASE}/complaints", json=payload, timeout=TIMEOUT)
    return _handle(response)


def lookup_complaint(ticket_id: str, access_code: str) -> dict[str, Any]:
    response = requests.post(
        f"{API_BASE}/complaints/{ticket_id}/lookup",
        json={"access_code": access_code},
        timeout=TIMEOUT,
    )
    return _handle(response)


def add_follow_up(ticket_id: str, access_code: str, text: str) -> dict[str, Any]:
    response = requests.post(
        f"{API_BASE}/complaints/{ticket_id}/messages",
        json={"access_code": access_code, "text": text},
        timeout=TIMEOUT,
    )
    return _handle(response)


def admin_headers(admin_token: str) -> dict[str, str]:
    return {"X-Admin-Token": admin_token}


def admin_analytics(admin_token: str) -> dict[str, Any]:
    response = requests.get(f"{API_BASE}/admin/analytics", headers=admin_headers(admin_token), timeout=TIMEOUT)
    return _handle(response)


def admin_list_complaints(admin_token: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    response = requests.get(
        f"{API_BASE}/admin/complaints",
        headers=admin_headers(admin_token),
        params=params or {},
        timeout=TIMEOUT,
    )
    return _handle(response)


def admin_get_complaint(admin_token: str, ticket_id: str) -> dict[str, Any]:
    response = requests.get(
        f"{API_BASE}/admin/complaints/{ticket_id}",
        headers=admin_headers(admin_token),
        timeout=TIMEOUT,
    )
    return _handle(response)


def admin_reply(admin_token: str, ticket_id: str, text: str) -> dict[str, Any]:
    response = requests.post(
        f"{API_BASE}/admin/complaints/{ticket_id}/messages",
        headers=admin_headers(admin_token),
        json={"text": text},
        timeout=TIMEOUT,
    )
    return _handle(response)


def admin_update_status(admin_token: str, ticket_id: str, status: str) -> dict[str, Any]:
    response = requests.patch(
        f"{API_BASE}/admin/complaints/{ticket_id}/status",
        headers=admin_headers(admin_token),
        json={"status": status},
        timeout=TIMEOUT,
    )
    return _handle(response)
