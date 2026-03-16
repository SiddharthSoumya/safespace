from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

ALLOWED_CATEGORIES = {
    "verbal harassment",
    "physical harassment",
    "digital harassment",
    "other",
}

ALLOWED_STATUSES = {"OPEN", "UNDER_REVIEW", "RESOLVED", "CLOSED"}


class ComplaintCreate(BaseModel):
    text: str = Field(..., min_length=10, max_length=5000)
    identity: str | None = Field(default=None, max_length=120)
    department: str | None = Field(default=None, max_length=80)
    use_auto_classification: bool = True
    manual_category: str | None = Field(default=None, max_length=50)

    @field_validator("manual_category")
    @classmethod
    def validate_manual_category(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip().lower()
        if normalized not in ALLOWED_CATEGORIES:
            raise ValueError(f"manual_category must be one of: {sorted(ALLOWED_CATEGORIES)}")
        return normalized


class ComplaintCreated(BaseModel):
    status: str
    ticket_id: str
    access_code: str
    category: str
    severity: str
    created_at: datetime
    message: str


class AccessCodeRequest(BaseModel):
    access_code: str = Field(..., min_length=4, max_length=40)


class ComplaintMessageCreate(AccessCodeRequest):
    text: str = Field(..., min_length=1, max_length=2000)


class AdminMessageCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class StatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        upper = value.upper()
        if upper not in ALLOWED_STATUSES:
            raise ValueError(f"status must be one of: {sorted(ALLOWED_STATUSES)}")
        return upper


class ComplaintMessageOut(BaseModel):
    sender_role: Literal["complainant", "admin"]
    text: str
    created_at: datetime


class ComplaintDetail(BaseModel):
    ticket_id: str
    text: str
    identity: str | None
    department: str | None
    category: str
    severity: str
    status: str
    created_at: datetime
    updated_at: datetime
    messages: list[ComplaintMessageOut]


class ComplaintSummary(BaseModel):
    ticket_id: str
    category: str
    severity: str
    department: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    preview: str


class AnalyticsResponse(BaseModel):
    total_complaints: int
    by_category: dict[str, int]
    by_severity: dict[str, int]
    by_status: dict[str, int]
    by_department: dict[str, int]
    daily_submissions: dict[str, int]
