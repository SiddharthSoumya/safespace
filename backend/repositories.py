from __future__ import annotations

from collections import Counter
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.core.security import decrypt_text, encrypt_text, generate_access_code, generate_ticket_id, hash_access_code
from backend.db.models import Complaint, ComplaintMessage
from backend.schemas import AnalyticsResponse, ComplaintDetail, ComplaintMessageOut, ComplaintSummary
from backend.services.classifier import classify_text, infer_severity


def create_complaint(
    db: Session,
    *,
    text: str,
    identity: str | None,
    department: str | None,
    use_auto_classification: bool,
    manual_category: str | None,
):
    category: str
    confidence = 0.0

    if use_auto_classification:
        category, confidence = classify_text(text)
    else:
        category = manual_category or "other"

    severity = infer_severity(text, confidence)

    ticket_id = generate_ticket_id()
    while db.scalar(select(Complaint).where(Complaint.ticket_id == ticket_id)) is not None:
        ticket_id = generate_ticket_id()

    access_code = generate_access_code()

    complaint = Complaint(
        ticket_id=ticket_id,
        access_code_hash=hash_access_code(access_code),
        encrypted_text=encrypt_text(text) or "",
        encrypted_identity=encrypt_text(identity),
        category=category,
        severity=severity,
        manual_category=manual_category,
        department=department,
        status="OPEN",
    )
    db.add(complaint)
    db.flush()

    first_message = ComplaintMessage(
        complaint_id=complaint.id,
        sender_role="complainant",
        encrypted_message=encrypt_text(text) or "",
    )
    db.add(first_message)
    db.commit()
    db.refresh(complaint)
    return complaint, access_code


def verify_access_code(complaint: Complaint, provided_code: str) -> bool:
    return complaint.access_code_hash == hash_access_code(provided_code.strip())


def _serialize_detail(complaint: Complaint) -> ComplaintDetail:
    messages = [
        ComplaintMessageOut(
            sender_role=message.sender_role,
            text=decrypt_text(message.encrypted_message) or "",
            created_at=message.created_at,
        )
        for message in complaint.messages
    ]
    return ComplaintDetail(
        ticket_id=complaint.ticket_id,
        text=decrypt_text(complaint.encrypted_text) or "",
        identity=decrypt_text(complaint.encrypted_identity),
        department=complaint.department,
        category=complaint.category,
        severity=complaint.severity,
        status=complaint.status,
        created_at=complaint.created_at,
        updated_at=complaint.updated_at,
        messages=messages,
    )


def get_complaint_by_ticket(db: Session, ticket_id: str) -> Complaint | None:
    stmt = (
        select(Complaint)
        .where(Complaint.ticket_id == ticket_id)
        .options(selectinload(Complaint.messages))
    )
    return db.scalar(stmt)


def get_complaint_detail_for_user(db: Session, ticket_id: str, access_code: str) -> ComplaintDetail | None:
    complaint = get_complaint_by_ticket(db, ticket_id)
    if complaint is None or not verify_access_code(complaint, access_code):
        return None
    return _serialize_detail(complaint)


def get_complaint_detail_for_admin(db: Session, ticket_id: str) -> ComplaintDetail | None:
    complaint = get_complaint_by_ticket(db, ticket_id)
    if complaint is None:
        return None
    return _serialize_detail(complaint)


def add_user_message(db: Session, ticket_id: str, access_code: str, text: str) -> ComplaintDetail | None:
    complaint = get_complaint_by_ticket(db, ticket_id)
    if complaint is None or not verify_access_code(complaint, access_code):
        return None

    message = ComplaintMessage(
        complaint_id=complaint.id,
        sender_role="complainant",
        encrypted_message=encrypt_text(text) or "",
    )
    db.add(message)
    db.commit()
    return get_complaint_detail_for_user(db, ticket_id, access_code)


def add_admin_message(db: Session, ticket_id: str, text: str) -> ComplaintDetail | None:
    complaint = get_complaint_by_ticket(db, ticket_id)
    if complaint is None:
        return None

    if complaint.status == "OPEN":
        complaint.status = "UNDER_REVIEW"

    message = ComplaintMessage(
        complaint_id=complaint.id,
        sender_role="admin",
        encrypted_message=encrypt_text(text) or "",
    )
    db.add(message)
    db.commit()
    return get_complaint_detail_for_admin(db, ticket_id)


def update_complaint_status(db: Session, ticket_id: str, status: str) -> ComplaintDetail | None:
    complaint = get_complaint_by_ticket(db, ticket_id)
    if complaint is None:
        return None
    complaint.status = status
    db.commit()
    return get_complaint_detail_for_admin(db, ticket_id)


def list_complaints(
    db: Session,
    *,
    status: str | None = None,
    category: str | None = None,
    severity: str | None = None,
    department: str | None = None,
) -> list[ComplaintSummary]:
    stmt = select(Complaint).order_by(Complaint.created_at.desc())
    if status:
        stmt = stmt.where(Complaint.status == status)
    if category:
        stmt = stmt.where(Complaint.category == category)
    if severity:
        stmt = stmt.where(Complaint.severity == severity)
    if department:
        stmt = stmt.where(Complaint.department == department)

    complaints = list(db.scalars(stmt))
    results: list[ComplaintSummary] = []
    for complaint in complaints:
        preview = (decrypt_text(complaint.encrypted_text) or "").replace("\n", " ")
        if len(preview) > 120:
            preview = preview[:117] + "..."
        results.append(
            ComplaintSummary(
                ticket_id=complaint.ticket_id,
                category=complaint.category,
                severity=complaint.severity,
                department=complaint.department,
                status=complaint.status,
                created_at=complaint.created_at,
                updated_at=complaint.updated_at,
                preview=preview,
            )
        )
    return results


def build_analytics(db: Session) -> AnalyticsResponse:
    complaints = list(db.scalars(select(Complaint)))
    by_category = Counter(c.category for c in complaints)
    by_severity = Counter(c.severity for c in complaints)
    by_status = Counter(c.status for c in complaints)
    by_department = Counter(c.department or "Unspecified" for c in complaints)
    by_day = Counter(
        (
            c.created_at.date().isoformat()
            if hasattr(c.created_at, "date")
            else datetime.utcnow().date().isoformat()
        )
        for c in complaints
    )

    return AnalyticsResponse(
        total_complaints=len(complaints),
        by_category=dict(by_category),
        by_severity=dict(by_severity),
        by_status=dict(by_status),
        by_department=dict(by_department),
        daily_submissions=dict(sorted(by_day.items())),
    )
