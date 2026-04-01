import sys
import os
from datetime import datetime, timedelta
import logging
import json

# Use proper src package imports
from src.services.postingRulesService import PostingRulesService

def test_posting_rules():
    logging.basicConfig(level=logging.INFO)
    config_path = os.path.join(os.path.dirname(__file__), "..", "src", "config", "posting_rules.yaml")
    state_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "test_posting_state.json")
    
    # Ensure data dir exists
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    if os.path.exists(state_path):
        os.remove(state_path)

    service = PostingRulesService(config_path, state_path)

    print("\n--- Testing Timing Rules (Twitter) ---")
    t1 = datetime(2026, 3, 17, 10, 0)
    print(f"Can post at 10:00 (UTC)? {service.can_post('twitter', current_time=t1)}")

    print("\n--- Testing Frequency Rules (LinkedIn max 3/day) ---")
    print(f"Can post 1st LinkedIn? {service.can_post('linkedin', current_time=t1)}")
    service.record_post('linkedin', current_time=t1)

    print(f"Can post 2nd LinkedIn? {service.can_post('linkedin', current_time=t1 + timedelta(minutes=241))}")
    service.record_post('linkedin', current_time=t1 + timedelta(minutes=241))   

    print(f"Can post 3rd LinkedIn? {service.can_post('linkedin', current_time=t1 + timedelta(minutes=482))}")
    service.record_post('linkedin', current_time=t1 + timedelta(minutes=482))   

    print(f"Can post 4th LinkedIn? {service.can_post('linkedin', current_time=t1 + timedelta(minutes=723))}")

    print("\n--- Testing Interval Rules (Discord min 15m) ---")
    print(f"Can post 1st Discord? {service.can_post('discord', current_time=t1)}")
    service.record_post('discord', current_time=t1)
    print(f"Can post 2nd Discord at +10m? {service.can_post('discord', current_time=t1 + timedelta(minutes=10))}")
    print(f"Can post 2nd Discord at +16m? {service.can_post('discord', current_time=t1 + timedelta(minutes=16))}")

    print("\n--- Testing Guardrails ---")
    print(f"Can spend money? {service.can_post('twitter', content_type='spend_money')}")

    # Cleanup
    if os.path.exists(state_path):
        os.remove(state_path)

if __name__ == "__main__":
    test_posting_rules()
