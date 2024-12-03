from fastapi import FastAPI, Request, HTTPException
from app.routers import users, metric_discovery
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app with root_path for ALB path-based routing
app = FastAPI(root_path="/backend-metric-discovery")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log request details for debugging"""
    path = request.url.path
    logger.info(f"Request: {request.method} {path}")
    
    if path == "/health":
        logger.debug("Health check request received")
    
    try:
        response = await call_next(request)
        logger.info(f"Response status: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Request failed: {str(e)}")
        raise

# Health check endpoint
@app.get(
    "/health",
    include_in_schema=True,
    tags=["Health Check"],
    response_model=dict,
    summary="Public health check endpoint"
)
async def health_check():
    """
    Public health check endpoint for ALB.
    This endpoint is public and does not require authentication.
    """
    try:
        return {
            "status": "healthy",
            "service": "narrative",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include your routers
app.include_router(users.router, prefix="", tags=["Login & Signup"])
app.include_router(metric_discovery.router, prefix="", tags=["metric discovery"])

@app.get("/")
async def root():
    return {"message": "Welcome to Othor API"}