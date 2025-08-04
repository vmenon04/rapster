from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import time

from app.routes import audio, auth
from app.config import get_settings
from app.logger import get_logger, setup_logging
from app.exceptions import (
    MusicAppException, DatabaseError, FileUploadError, 
    AudioAnalysisError, ValidationError, ConfigurationError
)

# Initialize settings and logging
settings = get_settings()
logger = get_logger("main")

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="A modern music sharing and analysis API",
    version="1.0.0",
    debug=settings.debug,
)

# Include API routes
app.include_router(audio.router)
app.include_router(auth.router)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(f"{process_time:.4f}")
    return response


# Custom exception handlers
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle custom validation errors."""
    logger.warning(f"Validation error: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message, "error_type": "ValidationError"}
    )


@app.exception_handler(DatabaseError)
async def database_exception_handler(request: Request, exc: DatabaseError):
    """Handle database errors."""
    logger.error(f"Database error: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Database operation failed", "error_type": "DatabaseError"}
    )


@app.exception_handler(FileUploadError)
async def file_upload_exception_handler(request: Request, exc: FileUploadError):
    """Handle file upload errors."""
    logger.error(f"File upload error: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": exc.message, "error_type": "FileUploadError"}
    )


@app.exception_handler(AudioAnalysisError)
async def audio_analysis_exception_handler(request: Request, exc: AudioAnalysisError):
    """Handle audio analysis errors."""
    logger.error(f"Audio analysis error: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.message, "error_type": "AudioAnalysisError"}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI validation errors."""
    logger.warning(f"Request validation error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Request validation failed", "errors": exc.errors()}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "error_type": "UnexpectedError"}
    )


# Health check and root endpoints
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "health": "/audio/health"
    }


@app.get("/health")
async def health_check():
    """General health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "timestamp": time.time()
    }


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info(f"Starting {settings.app_name}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"CORS origins: {settings.cors_origins}")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    logger.info(f"Shutting down {settings.app_name}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )