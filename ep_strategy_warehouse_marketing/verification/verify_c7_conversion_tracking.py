import sys
import os
from sqlalchemy.orm import Session
from datetime import datetime, UTC

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'solution', 'backend'))

from src.models.database import SessionLocal, engine, Base
from src.models.Subscriber import Subscriber
from src.models.ConversionEvent import ConversionEvent
from src.services.subscriberService import SubscriberService
from src.services.conversionTrackingService import ConversionTrackingService

def verify_c7_conversion_tracking():
    print("--- Verifying C7: Conversion Tracking Pipeline ---")
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    print("1. Database tables created/verified.")
    
    db = SessionLocal()
    try:
        # Clear previous test data if any
        db.query(ConversionEvent).delete()
        db.query(Subscriber).filter(Subscriber.email == 'test_conversion@example.com').delete()
        db.commit()
        
        conv_service = ConversionTrackingService(db)
        sub_service = SubscriberService(db)
        
        # Test 1: Page View with UTM
        print("2. Testing Page View logging...")
        conv_service.log_event(
            event_type='page_view',
            utm_source='test_ad_source',
            utm_medium='cpc',
            url='http://localhost:3000/?utm_source=test_ad_source&utm_medium=cpc'
        )
        
        events = db.query(ConversionEvent).filter(ConversionEvent.event_type == 'page_view').all()
        assert len(events) > 0
        assert events[0].utm_source == 'test_ad_source'
        print("   - Page view recorded successfully.")
        
        # Test 2: Form Submission with UTM
        print("3. Testing Form Submission logging...")
        sub = sub_service.create_pending_subscriber(
            email='test_conversion@example.com',
            utm_source='test_ad_source',
            utm_medium='cpc',
            session_id='test_session_123'
        )
        
        # Check if form_submit event was created
        submit_events = db.query(ConversionEvent).filter(
            ConversionEvent.event_type == 'form_submit',
            ConversionEvent.subscriber_id == sub.id
        ).all()
        
        assert len(submit_events) > 0
        assert submit_events[0].utm_source == 'test_ad_source'
        assert submit_events[0].session_id == 'test_session_123'
        print("   - Form submission and event recorded successfully.")
        
        # Test 3: Confirmation linked to subscriber
        print("4. Testing Confirmation logging...")
        sub_service.confirm_subscriber(sub.confirmation_token)
        
        confirm_events = db.query(ConversionEvent).filter(
            ConversionEvent.event_type == 'confirmation',
            ConversionEvent.subscriber_id == sub.id
        ).all()
        
        assert len(confirm_events) > 0
        print("   - Confirmation event linked to subscriber recorded successfully.")
        
        # Test 4: Conversion Stats
        print("5. Testing Conversion Stats computation...")
        stats = conv_service.get_conversion_stats()
        assert len(stats) > 0
        found_test_source = False
        for s in stats:
            if s['utm_source'] == 'test_ad_source':
                found_test_source = True
                assert s['page_views'] == 1
                assert s['form_submits'] == 1
                assert s['confirmations'] == 1
                assert s['view_to_submit_ratio'] == 1.0
                assert s['submit_to_confirm_ratio'] == 1.0
        
        assert found_test_source
        print("   - Conversion stats computed correctly.")

        # Test 5: Missing UTM parameters should not break ingestion
        print("6. Testing event ingestion without UTM parameters...")
        conv_service.log_event(
            event_type='form_impression',
            session_id='missing_utm_session',
            url='http://localhost:3000/'
        )

        organic_stats = conv_service.get_conversion_stats()
        organic_entry = next((s for s in organic_stats if s['utm_source'] == 'organic'), None)
        assert organic_entry is not None
        assert organic_entry['form_impressions'] >= 1
        print("   - Missing UTM event ingested successfully and grouped as organic.")
        
        print("\n--- C7 VERIFICATION SUCCESSFUL ---")
        return True
        
    except Exception as e:
        print(f"\n--- C7 VERIFICATION FAILED: {str(e)} ---")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = verify_c7_conversion_tracking()
    sys.exit(0 if success else 1)
