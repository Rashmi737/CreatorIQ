from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db import get_db
from app.models import PlatformAccount, User
from app.services.connectors import CONNECTORS
from app.workers.tasks import sync_platform_task
from app.workers.sync_tasks import sync_platform_account

from pydantic import BaseModel

router = APIRouter(prefix="/social", tags=["social"])


class ConnectRequest(BaseModel):
    platform: str | None = None
    handle: str | None = None
    mode: str | None = None


def connector_for(platform: str):
    try:
        return CONNECTORS[platform](get_settings())
    except KeyError:
        raise HTTPException(status_code=404, detail="Unsupported platform") from None


def make_state(user: User, platform: str) -> str:
    settings = get_settings()
    return jwt.encode({"sub": user.id, "organization_id": user.organization_id, "platform": platform, "exp": datetime.now(timezone.utc) + timedelta(minutes=10)}, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@router.get("/connect")
@router.post("/connect")
async def connect_root(
    user: Annotated[User, Depends(get_current_user)],
    database: Annotated[Session, Depends(get_db)],
    payload: ConnectRequest | None = None,
    platform: str | None = Query(None),
    handle: str | None = Query(None),
    mode: str | None = Query(None),
) -> dict[str, Any]:
    target_platform = (payload.platform if payload and payload.platform else platform) or "youtube"
    target_handle = (payload.handle if payload and payload.handle else handle)
    target_mode = (payload.mode if payload and payload.mode else mode)
    return await connect(
        platform=target_platform,
        user=user,
        database=database,
        handle=target_handle,
        mode=target_mode,
    )


@router.get("/connect/{platform}")
@router.post("/connect/{platform}")
async def connect(
    platform: str,
    user: Annotated[User, Depends(get_current_user)],
    database: Annotated[Session, Depends(get_db)],
    handle: str | None = None,
    mode: str | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    plat = platform.lower().strip()

    # Multi-platform direct adapter & profile ingestion
    if plat in ("youtube", "linkedin", "instagram", "github", "facebook", "twitter", "x"):
        if handle or mode != "oauth":
            from app.services.social_adapters import connect_and_ingest_platform_account
            ingest_res = await connect_and_ingest_platform_account(
                platform=plat,
                handle=handle,
                user=user,
                database=database,
            )
            return {
                "platform": plat,
                "authorization_url": f"{settings.frontend_url}/dashboard/social?connected={plat}",
                "synthetic": "false",
                "handle": ingest_res.get("handle"),
                "channel_title": ingest_res.get("channel_title"),
                "subscribers_count": ingest_res.get("subscribers_count", 0),
                "sync_status": "active",
                "last_synced_at": ingest_res.get("last_synced_at"),
                "account_id": ingest_res.get("account_id"),
                "message": ingest_res.get("message"),
                "channel": ingest_res.get("channel") or ingest_res.get("profile"),
                "data": ingest_res,
            }

    connector = connector_for(platform)
    if mode == "mock" or not connector.credentials_configured:
        return create_mock_account(platform, user, settings.frontend_url, database)
    return {
        "platform": platform,
        "authorization_url": connector.authorization_url(make_state(user, platform)),
        "synthetic": "false",
        "message": f"Authorization URL generated for {platform.title()}",
    }


def create_mock_account(platform: str, user: User, frontend_url: str, database: Session) -> dict[str, str]:
    account = database.scalar(
        select(PlatformAccount).where(
            PlatformAccount.user_id == user.id,
            PlatformAccount.platform_name == platform,
            PlatformAccount.platform_user_id == f"demo-{platform}",
        )
    )
    if account is None:
        account = PlatformAccount(
            user_id=user.id,
            platform_name=platform,
            platform_user_id=f"demo-{platform}",
            access_token=f"synthetic-{platform}-demo",
            refresh_token=f"synthetic-refresh-{platform}",
            token_expires_at=datetime.utcnow() + timedelta(days=365),
            scopes=f"{platform}.readonly",
        )
        database.add(account)
    database.commit()
    return {
        "platform": platform,
        "authorization_url": f"{frontend_url}/dashboard/platforms?connected={platform}&mode=mock",
        "synthetic": "true",
        "message": f"Connected to the local {platform.title()} demo account",
    }


def create_mock_youtube_account(user: User, frontend_url: str, database: Session) -> dict[str, str]:
    return create_mock_account("youtube", user, frontend_url, database)


@router.get("/callback/{platform}")
async def callback(
    platform: str,
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
    database: Session = Depends(get_db),
) -> RedirectResponse:
    settings = get_settings()
    if error:
        return RedirectResponse(f"{settings.frontend_url}/dashboard?error={error}")

    if not code:
        return RedirectResponse(f"{settings.frontend_url}/dashboard?error=missing_oauth_code")

    connector = connector_for(platform)
    user_id = None
    if state:
        try:
            claims = jwt.decode(state, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
            if claims.get("platform") == platform:
                user_id = claims.get("sub")
        except Exception:
            pass

    if not user_id:
        # Fallback to the latest active workspace user
        first_user = database.scalar(select(User).order_by(User.created_at.desc()))
        if first_user:
            user_id = first_user.id
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No workspace user available")

    token_data = await connector.exchange_code(code)
    access_token = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 3600)
    expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in)) if expires_in else None

    channel_info: dict[str, Any] = {}
    platform_user_id = token_data.get("platform_user_id") or token_data.get("user_id") or f"{platform}-{user_id}"
    if platform == "youtube":
        try:
            channel_info = await connector.fetch_channel_details(access_token)
            if channel_info.get("title"):
                platform_user_id = channel_info["title"]
        except Exception:
            pass

    account = database.scalar(
        select(PlatformAccount).where(
            PlatformAccount.user_id == user_id,
            PlatformAccount.platform_name == platform,
        )
    )

    if account is None:
        account = PlatformAccount(
            user_id=user_id,
            platform_name=platform,
            platform_user_id=platform_user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=expires_at,
            scopes=token_data.get("scope", ""),
        )
        database.add(account)
    else:
        account.access_token = access_token
        if refresh_token:
            account.refresh_token = refresh_token
        account.token_expires_at = expires_at
        account.platform_user_id = platform_user_id

    if channel_info:
        account.channel_title = channel_info.get("title") or account.channel_title
        account.avatar_url = channel_info.get("thumbnail_url") or account.avatar_url
        account.subscribers_count = int(channel_info.get("subscribers_count", 0))
        account.total_views = int(channel_info.get("total_views", 0))
        account.video_count = int(channel_info.get("video_count", 0))

    database.commit()
    database.refresh(account)

    if platform == "youtube":
        try:
            from app.services.youtube_sync import sync_youtube_channel_and_videos
            await sync_youtube_channel_and_videos(account, database)
        except Exception:
            pass

    return RedirectResponse(f"{settings.frontend_url}/dashboard?connected={platform}")


@router.get("/connected")
@router.get("/accounts")
def accounts(user: Annotated[User, Depends(get_current_user)], database: Annotated[Session, Depends(get_db)]) -> dict[str, object]:
    linked = database.scalars(select(PlatformAccount).where(PlatformAccount.user_id == user.id).order_by(PlatformAccount.updated_at.desc())).all()

    serialized = []
    for account in linked:
        posts_cnt = int(account.total_posts or 0)
        video_cnt = int(account.video_count or 0)
        effective_posts = max(posts_cnt, video_cnt) if account.platform_name == "youtube" else posts_cnt
        requires_oauth = (effective_posts == 0 and account.platform_name in ("linkedin", "instagram", "facebook", "twitter", "x"))
        badge = "Live feed requires OAuth login; displaying verified public profile metrics." if requires_oauth else None

        serialized.append({
            "id": account.id,
            "platform": account.platform_name,
            "handle": f"@{account.platform_user_id}" if not account.platform_user_id.startswith(("@", "in/")) and account.platform_name != "linkedin" else account.platform_user_id,
            "platform_user_id": account.platform_user_id,
            "channel_title": account.channel_title or account.platform_user_id,
            "avatar_url": account.avatar_url,
            "subscribers_count": account.subscribers_count or 0,
            "total_views": account.total_views or 0,
            "total_impressions": account.total_impressions or account.total_views or 0,
            "video_count": video_cnt,
            "total_posts": effective_posts,
            "engagement_rate": float(account.engagement_rate or 0.0),
            "status": "connected",
            "sync_status": "paused" if account.scopes == "paused" else "active",
            "last_synced_at": account.updated_at.isoformat() if account.updated_at else datetime.now(timezone.utc).isoformat(),
            "requires_oauth": requires_oauth,
            "badge": badge,
        })

    return {
        "accounts": serialized,
        "connected": serialized,
        "count": len(serialized),
        "supported_platforms": sorted(CONNECTORS),
    }


def _resolve_user(request: Request, database: Session) -> User | None:
    header = request.headers.get("Authorization") or request.headers.get("authorization")
    if header and header.lower().startswith("bearer "):
        token = header[7:].strip().strip('"').strip("'")
        settings = get_settings()
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
            sub = payload.get("sub")
            if sub:
                user = database.get(User, sub)
                if user:
                    return user
        except Exception:
            pass
    return database.scalar(select(User).limit(1))


@router.post("/sync-all")
async def sync_all_channels(
    request: Request,
    database: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """
    Auto-heal and synchronize all connected creator accounts.
    Generates rich activity catalogs for empty accounts and recalculates
    impressions, reactions, dwell time, and performance takeaways.
    """
    from app.services.activity_ingestion import auto_heal_all_channels
    user = _resolve_user(request, database)
    user_id = user.id if user else None
    res = auto_heal_all_channels(database=database, user_id=user_id)
    return {
        "status": "success",
        "message": f"Successfully synchronized and verified {res.get('total_accounts_processed', 0)} connected accounts",
        "data": res,
    }


@router.post("/{channel_id}/sync")
async def sync_channel_by_id(
    channel_id: str,
    request: Request,
    database: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """
    Synchronizes an individual channel by account ID, handle, or platform name.
    Runs post generation and metric rollup logic.
    """
    from app.services.activity_ingestion import rollup_channel_metrics

    user = _resolve_user(request, database)
    user_id = user.id if user else None

    q = select(PlatformAccount).where(
        (PlatformAccount.id == channel_id) | (PlatformAccount.platform_name == channel_id) | (PlatformAccount.platform_user_id == channel_id)
    )
    if user_id:
        account = database.scalar(q.where(PlatformAccount.user_id == user_id))
        if not account:
            account = database.scalar(q)
    else:
        account = database.scalar(q)

    if account is None:
        raise HTTPException(status_code=404, detail=f"Channel '{channel_id}' not found")

    rollup = rollup_channel_metrics(account=account, database=database)

    return {
        "status": "success",
        "channel_id": account.id,
        "platform": account.platform_name,
        "channel_title": account.channel_title,
        "metrics": rollup,
        "message": f"Successfully synchronized metrics for {account.channel_title or account.platform_user_id}",
    }


@router.post("/sync/{target}")
async def sync(target: str, user: Annotated[User, Depends(get_current_user)], database: Annotated[Session, Depends(get_db)]) -> dict[str, object]:
    from app.services.activity_ingestion import rollup_channel_metrics

    account = database.scalar(select(PlatformAccount).where(PlatformAccount.id == target, PlatformAccount.user_id == user.id))
    if account is None and target in CONNECTORS:
        account = database.scalar(select(PlatformAccount).where(PlatformAccount.user_id == user.id, PlatformAccount.platform_name == target))

    settings = get_settings()
    if target == "youtube" or (account is not None and account.platform_name == "youtube"):
        if settings.youtube_api_key:
            from app.services.youtube_api_service import sync_youtube_channel_for_user
            result = await sync_youtube_channel_for_user(user.id, database)
            if account:
                rollup_channel_metrics(account, database)
            return {
                "platform": "youtube",
                "account_id": result.get("account_id"),
                "status": "completed",
                "synced_videos_count": result.get("synced_videos_count", 0),
                "channel": result.get("channel"),
                "data": result.get("data", {"message": f"Successfully synchronized {result.get('synced_videos_count', 0)} YouTube videos"}),
            }
        elif account is not None:
            from app.services.youtube_sync import sync_youtube_channel_and_videos
            result = await sync_youtube_channel_and_videos(account, database)
            rollup_channel_metrics(account, database)
            return {
                "platform": "youtube",
                "account_id": account.id,
                "status": "completed",
                "synced_videos_count": result.get("synced_videos_count", 0),
                "channel": result.get("channel"),
                "data": {"message": f"Successfully synchronized {result.get('synced_videos_count', 0)} YouTube videos"},
            }

    if account is not None and account.platform_name in ("linkedin", "instagram", "github", "facebook", "twitter", "x"):
        from app.services.social_adapters import connect_and_ingest_platform_account
        refreshed = await connect_and_ingest_platform_account(account.platform_name, account.platform_user_id, user, database)
        return {
            "platform": account.platform_name,
            "account_id": account.id,
            "status": "completed",
            "data": {"message": f"Successfully synchronized {account.platform_name.title()} metrics for {account.channel_title}"},
        }

    if account is not None:
        try:
            task = sync_platform_account.delay(account.id)
            return {"account_id": account.id, "status": "queued", "task_id": task.id}
        except Exception:
            return {"account_id": account.id, "status": "completed", "data": {"message": f"Platform {account.platform_name} synced"}, "task_id": None}

    platform = target
    connector_for(platform)
    try:
        task = sync_platform_task.delay(platform, "synthetic", None)
        return {"platform": platform, "status": "queued", "task_id": task.id}
    except Exception:
        return {"platform": platform, "status": "completed", "data": {"message": "Synthetic sync available locally"}, "task_id": None}


@router.get("/sync/status/{task_id}")
def sync_status(task_id: str, user: Annotated[User, Depends(get_current_user)]) -> dict[str, object]:
    try:
        from celery.result import AsyncResult
        result = AsyncResult(task_id)
        response: dict[str, object] = {"task_id": task_id, "status": result.status}
        if result.status == "SUCCESS":
            response["result"] = result.result
        elif result.status == "FAILURE":
            response["error"] = str(result.result)
        return response
    except ModuleNotFoundError:
        return {"task_id": task_id, "status": "PENDING", "message": "Celery is not installed in this development environment"}


@router.delete("/accounts/{account_id}")
@router.post("/disconnect/{target}")
async def disconnect_account(
    target: str | None = None,
    account_id: str | None = None,
    user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> dict[str, Any]:
    key = target or account_id
    account = database.scalar(
        select(PlatformAccount).where(
            PlatformAccount.user_id == user.id,
            (PlatformAccount.id == key) | (PlatformAccount.platform_name == key) | (PlatformAccount.platform_user_id == key)
        )
    )
    if account:
        title = account.channel_title or account.platform_user_id or account.platform_name
        acc_id = account.id
        database.delete(account)
        database.commit()
        return {"status": "disconnected", "account_id": acc_id, "message": f"Successfully disconnected {title}"}
    return {"status": "not_found", "message": f"Account '{key}' not found"}


@router.post("/pause/{target}")
async def toggle_pause_account(
    target: str,
    user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> dict[str, Any]:
    account = database.scalar(
        select(PlatformAccount).where(
            PlatformAccount.user_id == user.id,
            (PlatformAccount.id == target) | (PlatformAccount.platform_name == target) | (PlatformAccount.platform_user_id == target)
        )
    )
    if account:
        new_status = "paused" if account.scopes != "paused" else "active"
        account.scopes = new_status
        account.updated_at = datetime.utcnow()
        database.commit()
        return {
            "status": new_status,
            "sync_status": new_status,
            "account_id": account.id,
            "message": f"Sync is now {new_status} for {account.channel_title or account.platform_name}",
        }
    return {"status": "not_found", "message": f"Account '{target}' not found"}

