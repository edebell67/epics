import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.models.LinkedInAuth import LinkedInAuth, LinkedInConfig
from src.connectors.linkedinConnector import LinkedInConnector

def main():
    load_dotenv()
    
    client_id = os.getenv("LINKEDIN_CLIENT_ID")
    client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("Error: LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET must be set in .env")
        return

    auth = LinkedInAuth(client_id=client_id, client_secret=client_secret)
    config = LinkedInConfig(auth=auth)
    connector = LinkedInConnector(config)
    
    # 1. Get Auth URL
    auth_url = connector.get_authorization_url(state="random_state_string")
    print(f"\n1. Go to this URL to authorize the app:\n{auth_url}")
    
    # 2. Get Code from user
    print("\n2. After authorizing, you will be redirected to your callback URL.")
    code = input("Enter the 'code' parameter from the redirect URL: ").strip()
    
    if not code:
        print("Error: Code is required")
        return
        
    # 3. Exchange for Token
    token = connector.exchange_code_for_token(code)
    if token:
        print(f"\n3. Success! Access Token: {token}")
        
        # 4. Get Profile ID
        person_id = connector.get_user_profile()
        print(f"4. Person ID: {person_id}")
        
        print("\nUpdate your .env file with these values:")
        print(f"LINKEDIN_ACCESS_TOKEN={token}")
        print(f"LINKEDIN_PERSON_ID={person_id}")
    else:
        print("\n3. Failed to get access token.")

if __name__ == "__main__":
    main()
