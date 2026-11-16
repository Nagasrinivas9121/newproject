import datetime
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from server.api.v1.audit import router as audit_router
from server.api.v1.auth import router as auth_router
from server.api.v1.client_dashboard import router as client_router
from server.api.v1.families import router as families_router
from server.api.v1.pilgrims import router as pilgrims_router
from server.api.v1.reports import router as reports_router
from server.api.v1.subscriptions import router as subscriptions_router
from server.api.v1.super_admin import router as super_admin_router
from server.api.v1.sync import router as sync_router
from server.api.v1.tickets import router as tickets_router
from server.core.config import settings
from server.core.database import AsyncSessionLocal, engine, init_db
from server.core.security import hash_password
from server.models.user import User


async def seed_super_admin():
    """Ensure a bootstrap Super Administrator account exists on platform start."""
    async with AsyncSessionLocal() as db:
        q = select(User).where(User.email == settings.SUPER_ADMIN_EMAIL.lower())
        existing = (await db.execute(q)).scalars().first()
        if not existing:
            super_admin = User(
                tenant_id=None,  # Platform level
                email=settings.SUPER_ADMIN_EMAIL.lower(),
                hashed_password=hash_password(settings.SUPER_ADMIN_PASSWORD),
                full_name=settings.SUPER_ADMIN_NAME,
                role="SUPER_ADMIN",
                is_active=True,
            )
            db.add(super_admin)
            await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    # Initialize DB tables
    await init_db()
    # Seed platform super admin
    await seed_super_admin()
    yield
    # Graceful shutdown: close db engine
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Multi-Client SaaS Architecture & Cloud Security API for SRIVANI Booking Management",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers under API v1 prefix
api_prefix = settings.API_V1_STR
app.include_router(auth_router, prefix=api_prefix)
app.include_router(super_admin_router, prefix=api_prefix)
app.include_router(client_router, prefix=api_prefix)
app.include_router(families_router, prefix=api_prefix)
app.include_router(pilgrims_router, prefix=api_prefix)
app.include_router(tickets_router, prefix=api_prefix)
app.include_router(subscriptions_router, prefix=api_prefix)
app.include_router(reports_router, prefix=api_prefix)
app.include_router(audit_router, prefix=api_prefix)
app.include_router(sync_router, prefix=api_prefix)


@app.get("/super-admin-ui", response_class=HTMLResponse, tags=["Web UI"])
async def super_admin_ui():
    """Super Admin web interface."""
    path = os.path.join(os.path.dirname(__file__), "templates", "super_admin.html")
    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/client-ui", response_class=HTMLResponse, tags=["Web UI"])
async def client_ui():
    """Client workspace web interface."""
    path = os.path.join(os.path.dirname(__file__), "templates", "client_dashboard.html")
    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/health", tags=["Health & Diagnostics"])
async def health_check():
    """Service health check verifying backend status and database connectivity."""
    db_healthy = False
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            db_healthy = True
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "UNHEALTHY", "database": "DISCONNECTED", "error": str(e)},
        )

    return {
        "status": "HEALTHY",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database": "CONNECTED" if db_healthy else "ERROR",
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health",
        "status": "ONLINE",
    }
