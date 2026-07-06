# backend/app/main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.api.v1 import auth, turfs, bookings, payments, owner

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    yield
    # Shutdown
    logger.info("Shutting down application")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.DEBUG else ["yourdomain.com"]
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(turfs.router, prefix="/api/v1/turfs", tags=["Turfs"])
app.include_router(bookings.router, prefix="/api/v1/bookings", tags=["Bookings"])
#app.include_router(payments.router, prefix="/api/v1/payments", tags=["Payments"])
#app.include_router(owner.router, prefix="/api/v1/owner", tags=["Owner Dashboard"])
#app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["Webhooks"])

@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "version": settings.APP_VERSION,
        "docs": "/api/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}