from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.db.session import get_db
from backend.repositories import (
    add_admin_message,
    add_user_message,
    build_analytics,
    create_complaint,
    get_complaint_detail_for_admin,
    get_complaint_detail_for_user,
    list_complaints,
    update_complaint_status,
)
from backend.schemas import (
    AccessCodeRequest,
    AdminMessageCreate,
    AnalyticsResponse,
    ComplaintCreate,
    ComplaintCreated,
    ComplaintDetail,
    ComplaintMessageCreate,
    ComplaintSummary,
    StatusUpdate,
)

router = APIRouter()
settings = get_settings()


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


@router.post("/complaints", response_model=ComplaintCreated, status_code=status.HTTP_201_CREATED)
def submit_complaint(payload: ComplaintCreate, db: Session = Depends(get_db)) -> ComplaintCreated:
    complaint, access_code = create_complaint(
        db,
        text=payload.text,
        identity=payload.identity,
        department=payload.department,
        use_auto_classification=payload.use_auto_classification,
        manual_category=payload.manual_category,
    )
    return ComplaintCreated(
        status="success",
        ticket_id=complaint.ticket_id,
        access_code=access_code,
        category=complaint.category,
        severity=complaint.severity,
        created_at=complaint.created_at,
        message="Save this ticket ID and access code. The access code is shown only once.",
    )


@router.post("/complaints/{ticket_id}/lookup", response_model=ComplaintDetail)
def lookup_complaint(ticket_id: str, payload: AccessCodeRequest, db: Session = Depends(get_db)) -> ComplaintDetail:
    result = get_complaint_detail_for_user(db, ticket_id, payload.access_code)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found or access code invalid")
    return result


@router.post("/complaints/{ticket_id}/messages", response_model=ComplaintDetail)
def add_follow_up(ticket_id: str, payload: ComplaintMessageCreate, db: Session = Depends(get_db)) -> ComplaintDetail:
    result = add_user_message(db, ticket_id, payload.access_code, payload.text)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found or access code invalid")
    return result


@router.get("/admin/complaints", response_model=list[ComplaintSummary], dependencies=[Depends(require_admin)])
def admin_list_complaints(
    db: Session = Depends(get_db),
    status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    department: str | None = Query(default=None),
) -> list[ComplaintSummary]:
    return list_complaints(db, status=status, category=category, severity=severity, department=department)


@router.get("/admin/complaints/{ticket_id}", response_model=ComplaintDetail, dependencies=[Depends(require_admin)])
def admin_get_complaint(ticket_id: str, db: Session = Depends(get_db)) -> ComplaintDetail:
    result = get_complaint_detail_for_admin(db, ticket_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
    return result


@router.post("/admin/complaints/{ticket_id}/messages", response_model=ComplaintDetail, dependencies=[Depends(require_admin)])
def admin_reply(ticket_id: str, payload: AdminMessageCreate, db: Session = Depends(get_db)) -> ComplaintDetail:
    result = add_admin_message(db, ticket_id, payload.text)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
    return result


@router.patch("/admin/complaints/{ticket_id}/status", response_model=ComplaintDetail, dependencies=[Depends(require_admin)])
def admin_update_status(ticket_id: str, payload: StatusUpdate, db: Session = Depends(get_db)) -> ComplaintDetail:
    result = update_complaint_status(db, ticket_id, payload.status)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
    return result


@router.get("/admin/analytics", response_model=AnalyticsResponse, dependencies=[Depends(require_admin)])
def admin_analytics(db: Session = Depends(get_db)) -> AnalyticsResponse:
    return build_analytics(db)
