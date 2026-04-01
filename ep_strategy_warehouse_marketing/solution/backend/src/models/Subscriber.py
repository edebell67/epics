from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, Index
from datetime import datetime, UTC
from .database import Base

class Subscriber(Base):
    __tablename__ = 'subscribers'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    
    # Lifecycle state
    status = Column(String(50), default='pending', index=True) # pending, confirmed, unsubscribed
    
    # Confirmation workflow
    confirmation_token = Column(String(100), unique=True, nullable=True, index=True)
    confirmed_at = Column(DateTime, nullable=True)
    
    # Unsubscribe workflow
    unsubscribe_token = Column(String(100), unique=True, nullable=True, index=True)
    unsubscribed_at = Column(DateTime, nullable=True)
    
    # Preferences and metadata
    preferences = Column(JSON, nullable=True) # JSON payload for user interests, frequency, etc.
    source_tag = Column(String(100), nullable=True) # e.g., 'landing_page_main'
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    def __repr__(self):
        return f'<Subscriber(email=''{self.email}'', status={self.status})>'
