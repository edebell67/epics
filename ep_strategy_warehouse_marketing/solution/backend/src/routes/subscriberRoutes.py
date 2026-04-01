from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..models.database import get_db
from ..schemas.subscriber_schema import (
    SubscriberCreate, 
    SubscriberResponse, 
    SubscriberConfirmation,
    SubscriberUnsubscribe
)
from ..services.subscriberService import SubscriberService

router = APIRouter(
    prefix='/subscriptions',
    tags=['subscriptions'],
    responses={404: {'description': 'Not found'}},
)

# V20260321_1445 - C7: Added UTM tracking fields for submission attribution
@router.post('/', response_model=SubscriberResponse, status_code=status.HTTP_201_CREATED)
def create_subscription(
    subscription_in: SubscriberCreate,
    db: Session = Depends(get_db)
):
    service = SubscriberService(db)
    subscriber = service.create_pending_subscriber(
        email=subscription_in.email,
        full_name=subscription_in.full_name,
        preferences=subscription_in.preferences,
        source_tag=subscription_in.source_tag,
        utm_source=subscription_in.utm_source,
        utm_medium=subscription_in.utm_medium,
        utm_campaign=subscription_in.utm_campaign,
        utm_content=subscription_in.utm_content,
        utm_term=subscription_in.utm_term,
        session_id=subscription_in.session_id
    )
    return subscriber

@router.post('/confirm', status_code=status.HTTP_200_OK)
def confirm_subscription(
    confirm_in: SubscriberConfirmation,
    db: Session = Depends(get_db)
):
    service = SubscriberService(db)
    subscriber = service.confirm_subscriber(confirm_in.token)

    if not subscriber:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Invalid confirmation token'
        )

    return {'message': 'Subscription confirmed successfully', 'email': subscriber.email}

@router.post('/unsubscribe', status_code=status.HTTP_200_OK)
def unsubscribe_subscription(
    unsubscribe_in: SubscriberUnsubscribe,
    db: Session = Depends(get_db)
):
    service = SubscriberService(db)
    subscriber = service.unsubscribe_subscriber(unsubscribe_in.token)

    if not subscriber:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Invalid unsubscribe token'
        )

    return {'message': 'Unsubscribed successfully', 'email': subscriber.email}  

@router.get('/{email}', response_model=SubscriberResponse)
def get_subscription_status(
    email: str,
    db: Session = Depends(get_db)
):
    service = SubscriberService(db)
    subscriber = service.get_subscriber_by_email(email)

    if not subscriber:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Subscription not found'
        )
    return subscriber

@router.get('/status/{status}', response_model=List[SubscriberResponse])        
def list_subscribers_by_status(
    status: str,
    db: Session = Depends(get_db)
):
    service = SubscriberService(db)
    subscribers = service.get_subscribers_by_status(status)
    return subscribers
