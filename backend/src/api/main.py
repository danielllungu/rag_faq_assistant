import logging
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.core.database import db_manager
from src.core.config import config
from src.api.models.schemas import HealthCheckResponse
from src.api.routes import faq
import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting FAQ RAG System...")

    try:
        valid, errors = config.validate()
        if not valid:
            logger.error("Configuration validation failed:")
            for error in errors:
                logger.error(f"   • {error}")
            raise RuntimeError("Invalid configuration")

        db_manager.initialize_pool(minconn=2, maxconn=10)
        logger.info("Database connection pool initialized")

        if not db_manager.table_exists('faqs'):
            logger.error("Table 'faqs' does not exist")
            raise RuntimeError("Database not initialized. Run initialize.py first.")

        if not db_manager.table_exists('faq_variants'):
            logger.error("Table 'faq_variants' does not exist")
            raise RuntimeError("Database not initialized. Run initialize.py first.")

        faq_count = db_manager.get_table_count('faqs')
        variant_count = db_manager.get_table_count('faq_variants')

        logger.info(f"Database ready: {faq_count} FAQs, {variant_count} variants")

        if faq_count == 0:
            logger.warning("No FAQs in database. Run seed_database.py to populate.")

        logger.info("FAQ RAG System ready!")

        from src.api.services.auth import api_key_auth
        logger.info(f"API authentication enabled with {len(api_key_auth.valid_keys)} key(s)")

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

    yield

    logger.info("Shutting down FAQ RAG System...")
    db_manager.close_pool()
    logger.info("Database connections closed")
    logger.info("Shutdown complete")


app = FastAPI(
    title="FAQ RAG System",
    description="""
    FAQ system using hybrid Retrieval Augmented Generation & LLM.
    """,
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(faq.router)


@app.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Root endpoint",
    tags=["General"]
)
async def root():
    return {
        "message": "FAQ RAG System API",
        "version": "1.0.0",
        "health": "/health",
        "authentication": {
            "type": "API Key",
            "header": "X-API-Key",
        }
    }


@app.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    tags=["General"]
)
async def health_check():
    """
    Health check endpoint.
    Verifies database connectivity and system status.

    **Note:** This endpoint is public (no authentication required).
    """
    try:
        faq_count = db_manager.get_table_count('faqs')
        db_status = "connected"

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        db_status = "disconnected"
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "database": db_status,
                "timestamp": datetime.now().isoformat()
            }
        )

    return HealthCheckResponse(
        status="healthy",
        database=db_status,
        timestamp=datetime.now()
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal error occurred. Please try again later."
        }
    )


if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
