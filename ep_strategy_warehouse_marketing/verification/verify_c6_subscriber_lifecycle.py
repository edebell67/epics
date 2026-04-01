import sys
import os
from sqlalchemy.orm import Session
from datetime import datetime, UTC

# Set database URL for verification
os.environ['DATABASE_URL'] = 'sqlite:///test.db'

# Add src to path
# verification is in ep_strategy_warehouse_marketing/verification
# solution/backend is in ep_strategy_warehouse_marketing/solution/backend
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'solution', 'backend'))

from src.models.database import SessionLocal, Base, engine
from src.models.Subscriber import Subscriber
from src.services.subscriberService import SubscriberService

def verify_lifecycle():
    print('--- Verifying C6: Subscriber Lifecycle ---')
    
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    service = SubscriberService(db)
    
    email = 'test_lifecycle@example.com'
    
    # 1. Create pending subscriber
    print(f'1. Creating pending subscriber: {email}')
    subscriber = service.create_pending_subscriber(email=email, full_name='Test User', source_tag='verification')
    assert subscriber.status == 'pending'
    assert subscriber.email == email
    assert subscriber.confirmation_token is not None
    assert subscriber.unsubscribe_token is not None
    print(f'   PASS: Subscriber created in pending state.')
    
    conf_token = subscriber.confirmation_token
    unsub_token = subscriber.unsubscribe_token
    
    # 2. Confirm subscriber
    print(f'2. Confirming subscriber with token: {conf_token}')
    confirmed_sub = service.confirm_subscriber(conf_token)
    assert confirmed_sub.status == 'confirmed'
    assert confirmed_sub.confirmed_at is not None
    print(f'   PASS: Subscriber confirmed.')
    
    # 3. Unsubscribe subscriber
    print(f'3. Unsubscribing subscriber with token: {unsub_token}')
    unsub_sub = service.unsubscribe_subscriber(unsub_token)
    assert unsub_sub.status == 'unsubscribed'
    assert unsub_sub.unsubscribed_at is not None
    print(f'   PASS: Subscriber unsubscribed.')
    
    # 4. Filter by status
    print(f'4. Filtering by status \'unsubscribed\'')
    unsubs = service.get_subscribers_by_status('unsubscribed')
    assert any(s.email == email for s in unsubs)
    print(f'   PASS: Filtered list contains the unsubscribed user.')
    
    # 5. Cleanup
    print('5. Cleaning up test data...')
    db.delete(unsub_sub)
    db.commit()
    print('   Done.')
    
    db.close()
    print('--- VERIFICATION COMPLETE ---')

if __name__ == '__main__':
    try:
        verify_lifecycle()
    except Exception as e:
        print(f'VERIFICATION FAILED: {e}')
        sys.exit(1)
