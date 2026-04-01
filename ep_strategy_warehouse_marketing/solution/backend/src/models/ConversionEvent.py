from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from datetime import datetime, UTC
from .database import Base

# V20260321_1445 - C7: Added ConversionEvent model for tracking user funnel performance
class ConversionEvent(Base):
    __tablename__ = 'conversion_events'

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False, index=True) # page_view, form_impression, form_submit, confirmation
    session_id = Column(String(100), nullable=True, index=True)
    
    # URL and Source Attribution
    url = Column(String(500), nullable=True)
    utm_source = Column(String(100), nullable=True, index=True)
    utm_medium = Column(String(100), nullable=True)
    utm_campaign = Column(String(100), nullable=True)
    utm_content = Column(String(100), nullable=True)
    utm_term = Column(String(100), nullable=True)
    
    # Optional link to subscriber
    subscriber_id = Column(Integer, ForeignKey('subscribers.id'), nullable=True, index=True)
    
    # Metadata for specific event details
    event_metadata = Column(JSON, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    def __repr__(self):
        return f'<ConversionEvent(type={self.event_type}, source={self.utm_source}, created_at={self.created_at})>'
