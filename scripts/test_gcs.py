#!/usr/bin/env python3
"""
Test GCS Connection
===================

Simple script to verify GCS bucket access by uploading a test file.

Usage:
    python scripts/test_gcs.py
"""
import os
import sys
from datetime import datetime
from google.cloud import storage
from dotenv import load_dotenv


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


def build_credentials():
    """Build credentials from env vars directly."""
    from google.oauth2 import service_account
    
    # Read directly from env (bypass pydantic parsing issues)
    client_email = os.getenv("GCS_CLIENT_EMAIL")
    private_key = os.getenv("GCS_PRIVATE_KEY")
    project_id = os.getenv("GCP_PROJECT_ID")
    private_key_id = os.getenv("GCS_PRIVATE_KEY_ID")
    
    private_key = private_key.replace("\\n", "\n")
    creds_info = {
        "type": "service_account",
        "project_id": project_id,
        "private_key_id": private_key_id,
        "private_key": private_key,
        "client_email": client_email,
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    print("creds:", creds_info)
    return service_account.Credentials.from_service_account_info(creds_info)


def test_gcs_upload():
    print("=" * 50)
    print("🧪 GCS CONNECTION TEST")
    print("=" * 50)
    
    bucket_name = os.getenv("GCS_BUCKET_NAME", "regulatory-intelligence-results")
    project_id = os.getenv("GCP_PROJECT_ID")
    client_email = os.getenv("GCS_CLIENT_EMAIL")
    
    print(f"\nBucket: {bucket_name}")
    print(f"Project ID: {project_id or '(not set)'}")
    if client_email:
        print(f"Auth: env vars (client_email: {client_email})")
    else:
        print(f"Auth: default ADC")
    
    # Initialize client
    print("\n[1] Initializing GCS client...")
    try:
        credentials = build_credentials()
        if credentials:
            client = storage.Client(credentials=credentials, project=project_id)
        else:
            client = storage.Client()
        print("    ✅ Client initialized")
    except Exception as e:
        print(f"    ❌ Failed: {e}")
        return False
    
    # Get bucket
    print(f"\n[2] Accessing bucket '{bucket_name}'...")
    try:
        bucket = client.bucket(bucket_name)
        # Check if bucket exists
        if not bucket.exists():
            print(f"    ❌ Bucket does not exist")
            print(f"    Create it with: gsutil mb gs://{bucket_name}")
            return False
        print("    ✅ Bucket accessible")
    except Exception as e:
        print(f"    ❌ Failed: {e}")
        return False
    
    # Upload test file
    print("\n[3] Uploading test file...")
    timestamp = datetime.utcnow().isoformat()
    test_content = f"GCS connection test\nTimestamp: {timestamp}\nStatus: SUCCESS"
    blob_path = "test/connection_test.txt"
    
    try:
        blob = bucket.blob(blob_path)
        blob.upload_from_string(test_content, content_type="text/plain")
        print(f"    ✅ Uploaded to gs://{bucket_name}/{blob_path}")
    except Exception as e:
        print(f"    ❌ Upload failed: {e}")
        return False
    
    # Verify by reading back
    print("\n[4] Verifying upload...")
    try:
        downloaded = blob.download_as_string().decode("utf-8")
        if "SUCCESS" in downloaded:
            print("    ✅ File verified")
        else:
            print("    ⚠️ File content mismatch")
    except Exception as e:
        print(f"    ❌ Verification failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("✅ GCS CONNECTION TEST PASSED")
    print("=" * 50)
    print(f"\nTest file: gs://{bucket_name}/{blob_path}")
    return True


if __name__ == "__main__":
    success = test_gcs_upload()
    sys.exit(0 if success else 1)
