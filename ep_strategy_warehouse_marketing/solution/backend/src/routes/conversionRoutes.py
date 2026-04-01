from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List, Optional

from ..models.database import get_db
from ..schemas.conversion_schema import (
    ConversionEventCreate, 
    ConversionStatsResponse
)
from ..services.conversionTrackingService import ConversionTrackingService

router = APIRouter(
    prefix='/conversions',
    tags=['conversions'],
    responses={404: {'description': 'Not found'}},
)

# V20260321_1445 - C7: Added endpoint for frontend event ingestion
@router.post('/log', status_code=status.HTTP_201_CREATED)
def log_conversion_event(
    event_in: ConversionEventCreate,
    db: Session = Depends(get_db)
):
    service = ConversionTrackingService(db)
    event = service.log_event(
        event_type=event_in.event_type,
        session_id=event_in.session_id,
        url=event_in.url,
        utm_source=event_in.utm_source,
        utm_medium=event_in.utm_medium,
        utm_campaign=event_in.utm_campaign,
        utm_content=event_in.utm_content,
        utm_term=event_in.utm_term,
        event_metadata=event_in.event_metadata
    )
    return {'status': 'success', 'event_id': event.id}

@router.get('/stats', response_model=List[ConversionStatsResponse])
def get_conversion_stats(
    utm_source: Optional[str] = None,
    db: Session = Depends(get_db)
):
    service = ConversionTrackingService(db)
    return service.get_conversion_stats(utm_source)
