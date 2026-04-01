from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import datetime, UTC, timedelta
from typing import List, Optional, Dict, Any

from ..models.ConversionEvent import ConversionEvent

class ConversionTrackingService:
    # V20260321_1445 - C7: Service for logging and analyzing user conversion events
    def __init__(self, db: Session):
        self.db = db

    def log_event(self, 
                  event_type: str, 
                  session_id: Optional[str] = None,
                  url: Optional[str] = None,
                  utm_source: Optional[str] = None,
                  utm_medium: Optional[str] = None,
                  utm_campaign: Optional[str] = None,
                  utm_content: Optional[str] = None,
                  utm_term: Optional[str] = None,
                  subscriber_id: Optional[int] = None,
                  event_metadata: Optional[Dict[str, Any]] = None) -> ConversionEvent:
        
        new_event = ConversionEvent(
            event_type=event_type,
            session_id=session_id,
            url=url,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
            utm_term=utm_term,
            subscriber_id=subscriber_id,
            event_metadata=event_metadata
        )
        
        self.db.add(new_event)
        self.db.commit()
        self.db.refresh(new_event)
        return new_event

    def get_conversion_stats(self, utm_source: Optional[str] = None) -> List[Dict[str, Any]]:
        # Compute conversion ratios by source and stage
        query = self.db.query(
            ConversionEvent.utm_source,
            func.count(case((ConversionEvent.event_type == 'page_view', 1))).label('page_views'),
            func.count(case((ConversionEvent.event_type == 'form_impression', 1))).label('form_impressions'),
            func.count(case((ConversionEvent.event_type == 'form_submit', 1))).label('form_submits'),
            func.count(case((ConversionEvent.event_type == 'confirmation', 1))).label('confirmations')
        ).group_by(ConversionEvent.utm_source)
        
        if utm_source:
            query = query.filter(ConversionEvent.utm_source == utm_source)
            
        results = query.all()
        
        stats = []
        for res in results:
            views = res.page_views or 1 # Avoid division by zero
            submits = res.form_submits or 0
            
            stats.append({
                'utm_source': res.utm_source or 'organic',
                'page_views': res.page_views,
                'form_impressions': res.form_impressions,
                'form_submits': res.form_submits,
                'confirmations': res.confirmations,
                'view_to_submit_ratio': round(submits / views, 4) if views > 0 else 0,
                'submit_to_confirm_ratio': round(res.confirmations / submits, 4) if submits > 0 else 0
            })
            
        return stats
