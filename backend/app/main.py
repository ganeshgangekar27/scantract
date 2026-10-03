"""
ScanTract FastAPI application entrypoint.

Configures and starts the FastAPI application with all route modules.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from .api.routes.reports import router as reports_router
from .api.routes.explanations import router as explanations_router
from .api.routes.contracts import router as contracts_router
from .api.routes.pipeline import router as pipeline_router
from .db.database import get_db
from .db.models import Contract

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup/shutdown lifespan handler.
    Marks interrupted contracts as failed on startup.
    """
    # Startup: Mark interrupted contracts as failed
    async for db in get_db():
        try:
            from sqlalchemy import select, update
            
            # Find contracts stuck in intermediate stages
            interrupted_stages = ['classifying', 'detecting_risks', 'generating_explanations']
            
            stmt = select(Contract).where(Contract.pipeline_stage.in_(interrupted_stages))
            result = await db.execute(stmt)
            interrupted_contracts = result.scalars().all()
            
            count = 0
            for contract in interrupted_contracts:
                old_stage = contract.pipeline_stage
                contract.pipeline_stage = 'failed'
                contract.failed_stage = old_stage
                contract.error_message = f'Interrupted: server restarted during {old_stage}'
                count += 1
                logger.warning(
                    f"Contract {contract.id} marked as failed: was in stage '{old_stage}' during restart"
                )
            
            if count > 0:
                await db.commit()
                logger.info(f"Startup cleanup: marked {count} interrupted contract(s) as failed")
            else:
                logger.info("Startup cleanup: no interrupted contracts found")
                
        except Exception as e:
            logger.error(f"Startup cleanup failed: {e}")
            await db.rollback()
        finally:
            break  # Only use first db session
    
    yield
    
    # Shutdown: nothing to clean up yet
    logger.info("ScanTract API shutting down")


# Create FastAPI app
app = FastAPI(
    title="ScanTract API",
    description="Contract risk analysis and report generation API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(reports_router)
app.include_router(explanations_router)
app.include_router(contracts_router, prefix="/api/contracts", tags=["contracts"])
app.include_router(pipeline_router)

logger.info("ScanTract API initialized with routes: reports, explanations, contracts, pipeline")


@app.get("/")
async def root():
    """Root endpoint - API health check."""
    return {
        "message": "ScanTract API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
