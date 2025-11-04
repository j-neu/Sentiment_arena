"""
Sentiment Arena - FastAPI Backend
Main application entry point with REST and WebSocket endpoints
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import logging
import time
from typing import Dict, Any

from backend.logger import get_logger
from backend.config import settings
from backend.database.base import engine, SessionLocal, Base
from backend.api.routes import router as api_router
from backend.api.websocket import router as ws_router, connection_manager
from backend.services.scheduler import TradingScheduler
from backend.services.market_data import MarketDataService

logger = get_logger(__name__)

# Global scheduler instance
scheduler: TradingScheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info("Starting Sentiment Arena API...")

    # Create database tables
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    # Initialize and start scheduler
    global scheduler
    try:
        logger.info("Initializing trading scheduler...")
        # Create a database session for market data service
        db = SessionLocal()
        market_data = MarketDataService(db)
        scheduler = TradingScheduler(
            db=db,
            market_data_service=market_data,
            openrouter_api_key=settings.OPENROUTER_API_KEY,
            alphavantage_api_key=settings.ALPHAVANTAGE_API_KEY,
            finnhub_api_key=settings.FINNHUB_API_KEY
        )
        scheduler.start()
        logger.info("Trading scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}", exc_info=True)
        scheduler = None

    logger.info("Sentiment Arena API is ready!")

    yield

    # Shutdown
    logger.info("Shutting down Sentiment Arena API...")

    # Stop scheduler
    if scheduler:
        logger.info("Stopping trading scheduler...")
        scheduler.stop()
        logger.info("Scheduler stopped")

    # Close WebSocket connections
    await connection_manager.disconnect_all()

    logger.info("Sentiment Arena API shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Sentiment Arena API",
    description="AI-powered stock trading competition backend",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests with timing"""
    start_time = time.time()

    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = time.time() - start_time

    # Log response
    logger.info(
        f"Response: {request.method} {request.url.path} "
        f"Status: {response.status_code} Duration: {duration:.3f}s"
    )

    return response


# Error handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    logger.error(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "details": exc.errors(),
            "message": "Invalid request parameters"
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": str(exc) if settings.DEBUG else "An unexpected error occurred"
        }
    )


# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint
    Returns system status and component health
    """
    scheduler_status = "running" if scheduler and scheduler.scheduler.running else "stopped"

    return {
        "status": "healthy",
        "version": "1.0.0",
        "components": {
            "database": "connected",
            "scheduler": scheduler_status,
            "websocket": "active"
        }
    }


# Root endpoint
@app.get("/", tags=["System"])
async def root() -> Dict[str, Any]:
    """
    API root endpoint
    Returns basic API information
    """
    return {
        "name": "Sentiment Arena API",
        "version": "1.0.0",
        "description": "AI-powered stock trading competition",
        "docs": "/docs",
        "health": "/health"
    }


# Include routers
app.include_router(api_router, prefix="/api")
app.include_router(ws_router)


# Helper function to get scheduler instance
def get_scheduler() -> TradingScheduler:
    """Get the global scheduler instance"""
    return scheduler


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
