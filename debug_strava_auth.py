#!/usr/bin/env python3
"""
Debug script to check Strava authentication and scopes.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ultra_trainer.strava_mcp_server.server import StravaClient


def debug_strava_auth():
    """Debug Strava authentication and check scopes."""
    refresh_token = os.getenv("STRAVA_REFRESH_TOKEN")
    client_id = os.getenv("STRAVA_CLIENT_ID")
    client_secret = os.getenv("STRAVA_CLIENT_SECRET")
    
    if not all([refresh_token, client_id, client_secret]):
        print("❌ Missing required environment variables:")
        if not refresh_token:
            print("  - STRAVA_REFRESH_TOKEN")
        if not client_id:
            print("  - STRAVA_CLIENT_ID")  
        if not client_secret:
            print("  - STRAVA_CLIENT_SECRET")
        return
    
    print("✅ All required environment variables are set")
    
    # Test token refresh
    client = StravaClient(refresh_token, client_id, client_secret)
    
    try:
        print("\n🔄 Testing token refresh...")
        client._refresh_token()
        print(f"✅ Token refresh successful!")
        print(f"   Access token: {client.access_token[:20]}...")
        print(f"   Expires at: {client.expires_at}")
        
        # Test API call to get athlete info (requires less permissions)
        print("\n🔍 Testing basic athlete endpoint...")
        athlete_info = client._make_request("athlete")
        print(f"✅ Athlete API call successful!")
        print(f"   Athlete: {athlete_info.get('firstname', 'Unknown')} {athlete_info.get('lastname', 'Unknown')}")
        
        # Test activities endpoint (requires activity:read scope)
        print("\n🏃 Testing activities endpoint...")
        activities = client._make_request("athlete/activities", {"per_page": 1})
        print(f"✅ Activities API call successful!")
        print(f"   Found {len(activities)} activities")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
        if "activity:read_permission" in str(e):
            print("\n🔧 SOLUTION NEEDED:")
            print("Your Strava app doesn't have the 'activity:read' scope.")
            print("You need to re-authorize your app with the correct scope.")
            print("\nTo fix this:")
            print("1. Go to: https://www.strava.com/oauth/authorize")
            print(f"2. Add these parameters:")
            print(f"   - client_id={client_id}")
            print(f"   - response_type=code")
            print(f"   - redirect_uri=http://localhost")
            print(f"   - approval_prompt=force")
            print(f"   - scope=activity:read")
            print("\n3. Complete the authorization and get a new refresh token")
            
            # Construct the full URL
            auth_url = (
                f"https://www.strava.com/oauth/authorize?"
                f"client_id={client_id}&"
                f"response_type=code&"
                f"redirect_uri=http://localhost&"
                f"approval_prompt=force&"
                f"scope=activity:read"
            )
            print(f"\n🔗 Direct authorization URL:")
            print(auth_url)
    
    finally:
        client.close()


if __name__ == "__main__":
    debug_strava_auth()
