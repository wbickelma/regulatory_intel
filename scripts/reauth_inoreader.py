#!/usr/bin/env python3
"""
Re-authorize Inoreader OAuth
============================

Run this when your refresh token expires.

Usage:
    python scripts/reauth_inoreader.py
"""
import os
import sys
import webbrowser

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
from clients.inoreader import InoreaderAuthManager

def main():
    load_dotenv()
    
    app_id = os.getenv("CLIENT_ID_INOREADER")
    app_key = os.getenv("CLIENT_SECRET_INOREADER")
    
    if not app_id or not app_key:
        print("❌ Missing CLIENT_ID_INOREADER or CLIENT_SECRET_INOREADER in .env")
        return
    
    auth = InoreaderAuthManager(app_id=app_id, app_key=app_key)
    redirect_uri = "http://localhost"
    
    # Check if code provided as argument
    if len(sys.argv) > 1:
        auth_code = sys.argv[1].strip()
        print("=" * 60)
        print("🔐 INOREADER RE-AUTHORIZATION")
        print("=" * 60)
        print(f"\nUsing provided auth code: {auth_code[:20]}...")
    else:
        # Step 1: Generate auth URL
        auth_url = auth.get_auth_url(redirect_uri=redirect_uri)
        
        print("=" * 60)
        print("🔐 INOREADER RE-AUTHORIZATION")
        print("=" * 60)
        print("\n1. Opening browser to authorize...")
        print(f"\n   URL: {auth_url}\n")
        
        webbrowser.open(auth_url)
        
        print("2. After authorizing, you'll be redirected to a URL like:")
        print("   http://localhost/?code=XXXXX&state=774411")
        print("\n3. Copy the 'code' value from that URL and paste it below:\n")
        
        auth_code = input("   Enter auth code: ").strip()
    
    if not auth_code:
        print("❌ No code entered. Exiting.")
        return
    
    # Step 2: Exchange code for tokens
    try:
        tokens = auth.exchange_auth_code(auth_code, redirect_uri=redirect_uri)
        print("\n✅ SUCCESS! New tokens saved.")
        print(f"   Access token: {tokens['access_token'][:20]}...")
        print(f"   Refresh token: {tokens.get('refresh_token', 'N/A')[:20]}...")
        print(f"   Expires in: {tokens.get('expires_in', 'unknown')} seconds")
        print("\n   Tokens have been saved. You can now run the demo again.")
    except Exception as e:
        print(f"\n❌ Failed to exchange code: {e}")


if __name__ == "__main__":
    main()
