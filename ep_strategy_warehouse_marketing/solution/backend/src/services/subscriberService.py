from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, UTC
import secrets
from typing import List, Optional

from ..models.Subscriber import Subscriber
from ..models.SubscriberLifecycleEvent import SubscriberLifecycleEvent
from .conversionTrackingService import ConversionTrackingService # V20260321_1445 - C7

class SubscriberService:
    def __init__(self, db: Session):
        self.db = db

    def generate_token(self, length=64):
        return secrets.token_urlsafe(length)

    def create_pending_subscriber(self, 
                                  email: str, 
                                  full_name: Optional[str] = None, 
                                  preferences: Optional[dict] = None, 
                                  source_tag: Optional[str] = None,
                                  utm_source: Optional[str] = None,
                                  utm_medium: Optional[str] = None,
                                  utm_campaign: Optional[str] = None,
                                  utm_content: Optional[str] = None,
                                  utm_term: Optional[str] = None,
                                  session_id: Optional[str] = None) -> Subscriber:
        # V20260321_1445 - C7: Extended to handle UTM tracking and log conversion events
        email_lower = email.lower()
        existing = self.db.query(Subscriber).filter(func.lower(Subscriber.email) == email_lower).first()
        
        if existing:
            # If already confirmed, don't log another form submit, but if pending, we might want to log it?
            # For now, just return.
            return existing

        new_sub = Subscriber(
            email=email_lower,
            full_name=full_name,
            status='pending',
            confirmation_token=self.generate_token(),
            unsubscribe_token=self.generate_token(),
            preferences=preferences,
            source_tag=source_tag or utm_source
        )

        self.db.add(new_sub)
        self.db.commit()
        self.db.refresh(new_sub)
        self.db.add(
            SubscriberLifecycleEvent(
                subscriber_id=new_sub.id,
                event_type='created',
                status='pending',
                event_metadata={
                    'source_tag': source_tag,
                    'utm_source': utm_source,
                    'utm_campaign': utm_campaign,
                },
            )
        )
        self.db.commit()
        
        # Log conversion event
        conv_service = ConversionTrackingService(self.db)
        conv_service.log_event(
            event_type='form_submit',
            session_id=session_id,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
            utm_term=utm_term,
            subscriber_id=new_sub.id
        )
        
        return new_sub

    def confirm_subscriber(self, token: str) -> Optional[Subscriber]:
        # Validates confirmation token and moves subscriber to confirmed state. 
        subscriber = self.db.query(Subscriber).filter(Subscriber.confirmation_token == token).first()

        if not subscriber:
            return None

        if subscriber.status == 'pending':
            subscriber.status = 'confirmed'
            subscriber.confirmed_at = datetime.now(UTC)
            
            # V20260321_1445 - C7: Log confirmation event linked to subscriber
            conv_service = ConversionTrackingService(self.db)
            conv_service.log_event(
                event_type='confirmation',
                subscriber_id=subscriber.id,
                utm_source=subscriber.source_tag # Use source_tag as fallback for attribution
            )
            self.db.add(
                SubscriberLifecycleEvent(
                    subscriber_id=subscriber.id,
                    event_type='confirmed',
                    status='confirmed',
                    event_metadata={'confirmation_token_used': True},
                )
            )

        self.db.commit()
        self.db.refresh(subscriber)
        return subscriber

    def unsubscribe_subscriber(self, token: str) -> Optional[Subscriber]:       
        # Validates unsubscribe token and moves subscriber to unsubscribed state.
        subscriber = self.db.query(Subscriber).filter(Subscriber.unsubscribe_token == token).first()
        
        if not subscriber:
            return None

        subscriber.status = 'unsubscribed'
        subscriber.unsubscribed_at = datetime.now(UTC)
        self.db.add(
            SubscriberLifecycleEvent(
                subscriber_id=subscriber.id,
                event_type='unsubscribed',
                status='unsubscribed',
                event_metadata={'unsubscribe_token_used': True},
            )
        )

        self.db.commit()
        self.db.refresh(subscriber)
        return subscriber

    def get_subscribers_by_status(self, status: str) -> List[Subscriber]:       
        # Returns subscribers filtered by status.
        return self.db.query(Subscriber).filter(Subscriber.status == status).all()

    def get_subscriber_by_email(self, email: str) -> Optional[Subscriber]:      
        # Returns subscriber by email.
        return self.db.query(Subscriber).filter(func.lower(Subscriber.email) == email.lower()).first()
