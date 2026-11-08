from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBearer
from sqlalchemy import text

from app.api.router import router
from app.core.config import get_settings
from app.db import Base, engine
from app.db import mongodb, redis
from app.db.base import import_models
from app.db.schema import ensure_user_schema
from app.routers.analytics import router as analytics_router
from app.routers.auth import router as auth_router
from app.routers.monetization import router as monetization_router
from app.routers.notifications import router as notifications_router
from app.routers.social import router as social_router
from app.routers.social import callback as social_callback

settings = get_settings()
import_models()
ensure_user_schema()
logger = logging.getLogger("creatoriq.startup")


@asynccontextmanager
async def lifespan(_: FastAPI):
    google_id = settings.google_client_id_effective
    frontend_origin = (settings.frontend_url or "http://localhost:5173").rstrip("/")
    logger.info("Google OAuth Client ID: %s", google_id)
    print(
        f"\n=======================================================\n"
        f"[OAuth Boot Info]\n"
        f"  Google Client ID: {google_id}\n"
        f"  Authorized JavaScript Origin needed: {frontend_origin}\n"
        f"  OAuth Redirect URI: {settings.google_redirect_uri_effective}\n"
        f"=======================================================\n",
        flush=True,
    )
    if settings.environment == "development":
        Base.metadata.create_all(bind=engine)
    ensure_user_schema()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        await mongodb.connect()
        await mongodb.client.admin.command("ping")
        await redis.connect()
        await redis.get_client().ping()
    except Exception as error:
        await redis.disconnect()
        await mongodb.disconnect()
        if settings.environment != "development":
            raise
        logger.warning("Optional local infrastructure is unavailable: %s", error)
    try:
        yield
    finally:
        await redis.disconnect()
        await mongodb.disconnect()


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=settings.app_name,
        version="1.0.0",
        description="CreatorIQ API with Bearer token authentication",
        routes=app.routes,
    )
    openapi_schema.setdefault("components", {})
    openapi_schema["components"]["securitySchemes"] = {
        "HTTPBearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your Bearer token directly in the field below.",
        }
    }
    # Ensure secured routes in Swagger UI use HTTPBearer
    for path in openapi_schema.get("paths", {}).values():
        for operation in path.values():
            if isinstance(operation, dict) and "security" in operation:
                operation["security"] = [{"HTTPBearer": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

app.include_router(router)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(monetization_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(social_router, prefix="/api/v1")
app.add_api_route("/api/auth/{platform}/callback", social_callback, methods=["GET"], include_in_schema=False)
app.add_api_route("/api/auth/{platform}/callback/", social_callback, methods=["GET"], include_in_schema=False)


