from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import engine, Base
from app.routers import auth, clients, invoices, analytics, audit

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database schema on boot
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise Multi-Tenant Invoicing & Financial Operations Microservice Engine",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware for modern frontend frameworks (React, Vue, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Sub-Routers
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(clients.router, prefix=settings.API_V1_PREFIX)
app.include_router(invoices.router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics.router, prefix=settings.API_V1_PREFIX)
app.include_router(audit.router, prefix=settings.API_V1_PREFIX)

@app.get("/health", tags=["System Health"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database": "connected"
    }

@app.get("/", tags=["System Root"])
def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "docs": "/docs",
        "health": "/health",
        "api_v1": settings.API_V1_PREFIX
    }
