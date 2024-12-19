# routers/metric_discovery.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.utils.database import get_db
from uuid import UUID
from app.services.metric_discovery import MetricDiscoveryService
from app.models.models import MetricDefinition, AnalyticsConfiguration, DataSourceConnection
from app.utils.auth import get_current_user
from pydantic import BaseModel
from datetime import datetime
from openai import OpenAI
import os
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
metric_service = MetricDiscoveryService(client)

class MetricResponse(BaseModel):
    id: int
    name: str
    category: str
    calculation: str
    aggregation_period: str
    visualization_type: str
    confidence_score: float
    business_context: Optional[str]

    class Config:
        from_attributes = True

@router.post("/metrics/discover/{connection_id}", response_model=List[MetricResponse])
async def discover_metrics(
    connection_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Discover metrics for a data source connection."""
    try:
        # Verify user has access to the connection
        user = current_user["user"]
        org_id = current_user["current_org_id"]
        
        # Check connection exists and belongs to user's organization
        connection = db.query(DataSourceConnection).filter(
            DataSourceConnection.id == connection_id,
            DataSourceConnection.organization_id == org_id
        ).first()
        
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        # Discover metrics
        metrics = await metric_service.discover_metrics(connection_id, db)
        return metrics
        
    except Exception as e:
        logger.error(f"Error in discover_metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics/catalog/{connection_id}", response_model=List[MetricResponse])
async def get_metric_catalog(
    connection_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all discovered metrics for a connection."""
    try:
        metrics = db.query(MetricDefinition).filter(
            MetricDefinition.connection_id == connection_id
        ).all()
        return metrics
    except Exception as e:
        logger.error(f"Error in get_metric_catalog: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

class AnalyticsConfigCreate(BaseModel):
    metrics: List[int]  # List of metric IDs
    time_ranges: List[str]
    dimensions: List[str]
    refresh_schedule: Optional[str]

@router.post("/metrics/configure/{connection_id}")
async def configure_analytics(
    connection_id: UUID,
    config: AnalyticsConfigCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Configure analytics for selected metrics."""
    try:
        # Verify metrics exist
        metrics = db.query(MetricDefinition).filter(
            MetricDefinition.id.in_(config.metrics)
        ).all()
        
        if len(metrics) != len(config.metrics):
            raise HTTPException(status_code=400, detail="Invalid metric IDs provided")
        
        # Create analytics configuration
        analytics_config = AnalyticsConfiguration(
            connection_id=connection_id,
            metrics=config.metrics,
            time_ranges=config.time_ranges,
            dimensions=config.dimensions,
            refresh_schedule=config.refresh_schedule,
            priority_score=1.0  # Default priority
        )
        
        db.add(analytics_config)
        db.commit()
        
        return {"message": "Analytics configuration created successfully"}
        
    except Exception as e:
        logger.error(f"Error in configure_analytics: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))