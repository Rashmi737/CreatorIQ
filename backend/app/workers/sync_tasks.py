import asyncio
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.db import mongodb
from app.db.session import SessionLocal
from app.models import PlatformAccount
from app.services.connectors import CONNECTORS


async def _collect(account: PlatformAccount) -> dict[str, Any]:
    connector_class = CONNECTORS.get(account.platform_name)
    if connector_class is None:
        raise ValueError(f"Unsupported platform: {account.platform_name}")
    connector = connector_class(get_settings())
    metrics = await connector.fetch_metrics(account.access_token, account.platform_user_id)
    return {
        "account_id": account.id,
        "platform": account.platform_name,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "payload": metrics,
    }


@celery_app.task(name="app.workers.sync_tasks.sync_platform_account")
def sync_platform_account(account_id: str) -> dict[str, Any]:
    database = SessionLocal()
    try:
        account = database.get(PlatformAccount, account_id)
        if account is None:
            raise ValueError(f"Platform account {account_id} was not found")
        raw_payload = asyncio.run(_collect(account))
        if mongodb.database is not None:
            asyncio.run(mongodb.database["raw_social_feeds"].insert_one(raw_payload))
        account.updated_at = datetime.utcnow()
        database.commit()
        return {"account_id": account.id, "platform": account.platform_name, "status": "synced", "collected_at": raw_payload["collected_at"]}
    except Exception:
        database.rollback()
        raise
    finally:
        database.close()


@celery_app.task(name="app.workers.sync_tasks.sync_all_active_accounts")
def sync_all_active_accounts() -> list[str]:
    database = SessionLocal()
    try:
        account_ids = list(database.scalars(select(PlatformAccount.id)).all())
    finally:
        database.close()
    return [sync_platform_account.delay(account_id).id for account_id in account_ids]


@celery_app.task(name="app.workers.sync_tasks.stream_realtime_metrics")
def stream_realtime_metrics() -> dict[str, Any]:
    """Background task that simulates real-time metrics updates in Redis."""
    try:
        from app.db import redis
        import random
        
        redis_client = redis.get_client()
        if redis_client is None:
            return {"status": "redis_unavailable"}
        
        # Simulate live metrics increments
        current_viewers = int(redis_client.hget("realtime:live", "current_viewers") or 1200)
        current_viewers += random.randint(-10, 50)
        
        metrics = {
            "current_viewers": max(0, current_viewers),
            "likes_per_minute": round(random.uniform(10, 25), 1),
            "comments_per_minute": round(random.uniform(1, 8), 1),
            "shares_per_minute": round(random.uniform(0.1, 2), 1),
            "reach_delta": random.randint(500, 3000),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        
        # Store in Redis hash
        redis_client.hset("realtime:live", mapping={k: str(v) for k, v in metrics.items()})
        redis_client.expire("realtime:live", 3600)  # Expire after 1 hour
        
        return {"status": "success", "metrics": metrics}
    except Exception as error:
        return {"status": "error", "error": str(error)}
