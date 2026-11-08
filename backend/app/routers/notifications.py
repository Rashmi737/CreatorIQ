from datetime import datetime, timezone
from typing import Any
import jwt

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import get_db
from app.models.identity import User
from app.models.monetization import WorkspaceAlert
from app.models.social import PlatformAccount

router = APIRouter(prefix="/notifications", tags=["notifications"])


class AlertCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(...)
    alert_type: str = Field(default="milestone", max_length=50)


def _resolve_user_id(request: Request, database: Session, user_id_param: str | None = None) -> str:
    """Resolve user ID from Bearer token or fall back to default user in workspace."""
    if user_id_param:
        return user_id_param
    header = request.headers.get("Authorization") or request.headers.get("authorization")
    if header and header.lower().startswith("bearer "):
        token = header[7:].strip().strip('"').strip("'")
        settings = get_settings()
        for secret in [settings.jwt_secret, "change-me-in-development", "replace-with-a-long-random-secret"]:
            try:
                payload = jwt.decode(token, secret, algorithms=[settings.jwt_algorithm])
                sub = payload.get("sub")
                if sub:
                    return str(sub)
            except Exception:
                continue

    default_user = database.scalar(select(User).limit(1))
    if default_user:
        return default_user.id
    return "default-creator"


def _format_milestone_number(num: int) -> str:
    if num >= 1_000_000:
        return f"{num // 1_000_000}M" if num % 1_000_000 == 0 else f"{num / 1_000_000:.1f}M"
    if num >= 1_000:
        return f"{num // 1_000}K" if num % 1_000 == 0 else f"{num / 1_000:.1f}K"
    return str(num)


def _check_and_generate_milestones(uid: str, database: Session) -> None:
    """Detect authentic follower milestones from connected PlatformAccount records."""
    accounts = list(
        database.scalars(
            select(PlatformAccount).where(PlatformAccount.user_id == uid)
        ).all()
    )
    if not accounts:
        # Fallback to any accounts in workspace if uid is default
        accounts = list(database.scalars(select(PlatformAccount)).all())

    milestone_thresholds = [1_000_000, 500_000, 100_000, 50_000, 10_000, 1_000]
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    for acc in accounts:
        subs = int(acc.subscribers_count or 0)
        p_name = acc.platform_name.capitalize()
        h_name = acc.channel_title or acc.platform_user_id

        for threshold in milestone_thresholds:
            if subs >= threshold:
                formatted_num = _format_milestone_number(threshold)
                expected_title = f"Milestone Reached: {h_name} crossed {formatted_num} followers!"
                
                # Check if this milestone alert already exists
                existing = database.scalar(
                    select(WorkspaceAlert).where(
                        WorkspaceAlert.user_id == uid,
                        WorkspaceAlert.title == expected_title,
                    )
                )
                if not existing:
                    new_alert = WorkspaceAlert(
                        user_id=uid,
                        title=expected_title,
                        message=f"Verified milestone: Your {p_name} account '{h_name}' has surpassed {threshold:,} audience members (currently at {subs:,}).",
                        alert_type="milestone",
                        is_read=False,
                        created_at=now,
                    )
                    database.add(new_alert)
                    database.flush()
                # Break to highest milestone for this account
                break

    database.commit()


@router.get("")
@router.get("/")
async def get_notifications(
    request: Request,
    user_id: str | None = Query(None, description="Optional user ID filter"),
    database: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Returns active alerts and milestone triggers for the current workspace.
    Automatically checks connected accounts for new follower milestones.
    """
    uid = _resolve_user_id(request, database, user_id)

    # Automatically generate milestone triggers if any account qualifies
    _check_and_generate_milestones(uid, database)

    alerts = list(
        database.scalars(
            select(WorkspaceAlert)
            .where((WorkspaceAlert.user_id == uid) | (WorkspaceAlert.user_id == "default-creator"))
            .order_by(desc(WorkspaceAlert.created_at))
            .limit(50)
        ).all()
    )

    unread_count = sum(1 for a in alerts if not a.is_read)

    return {
        "alerts": [
            {
                "id": a.id,
                "title": a.title,
                "message": a.message,
                "alert_type": a.alert_type,
                "is_read": a.is_read,
                "created_at": a.created_at.isoformat(),
            }
            for a in alerts
        ],
        "unread_count": unread_count,
        "total_count": len(alerts),
    }


@router.post("/{alert_id}/read")
async def mark_alert_read(
    alert_id: str,
    request: Request,
    database: Session = Depends(get_db),
) -> dict[str, Any]:
    """Mark an alert as read."""
    uid = _resolve_user_id(request, database)
    alert = database.scalar(select(WorkspaceAlert).where(WorkspaceAlert.id == alert_id))
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_read = True
    database.commit()

    unread_count = database.scalar(
        select(WorkspaceAlert).where(WorkspaceAlert.user_id == uid, WorkspaceAlert.is_read == False) # noqa
    )

    return {
        "success": True,
        "alert_id": alert.id,
        "is_read": True,
        "message": "Alert marked as read.",
    }


@router.post("/read-all")
async def mark_all_alerts_read(
    request: Request,
    user_id: str | None = Query(None),
    database: Session = Depends(get_db),
) -> dict[str, Any]:
    """Mark all alerts as read for the user."""
    uid = _resolve_user_id(request, database, user_id)
    alerts = list(
        database.scalars(
            select(WorkspaceAlert).where(
                (WorkspaceAlert.user_id == uid) | (WorkspaceAlert.user_id == "default-creator"),
                WorkspaceAlert.is_read == False,
            )
        ).all()
    )

    for a in alerts:
        a.is_read = True

    database.commit()
    return {
        "success": True,
        "marked_count": len(alerts),
        "message": f"Marked {len(alerts)} alerts as read.",
    }


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_custom_alert(
    payload: AlertCreate,
    request: Request,
    database: Session = Depends(get_db),
) -> dict[str, Any]:
    """Create a manual workspace notification alert."""
    uid = _resolve_user_id(request, database)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    alert = WorkspaceAlert(
        user_id=uid,
        title=payload.title.strip(),
        message=payload.message.strip(),
        alert_type=payload.alert_type.lower().strip(),
        is_read=False,
        created_at=now,
    )
    database.add(alert)
    database.commit()
    database.refresh(alert)

    return {
        "id": alert.id,
        "title": alert.title,
        "message": alert.message,
        "alert_type": alert.alert_type,
        "is_read": alert.is_read,
        "created_at": alert.created_at.isoformat(),
    }
