"""
Admin actions triggered by GitHub Actions.

Handles CRUD operations for users, topics, and sources.
Syncs data to GCS and generates JSON for the frontend.

Usage:
    python scripts/admin_action.py sync
    python scripts/admin_action.py add-user --name "John Doe" --email "john@example.com" --topics "1,2,3"
    python scripts/admin_action.py delete-user --user-id 1
    python scripts/admin_action.py add-topic --name "AI Governance"
    python scripts/admin_action.py delete-topic --topic-id 1
    python scripts/admin_action.py add-source --name "FCC News" --url "https://fcc.gov" --country "US" --topics "1,2"
    python scripts/admin_action.py delete-source --source-id 1
"""
import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from clients.db_client import DBClient
from clients.rss_app import RssAppClient
from clients.inoreader import InoreaderClient, InoreaderAuthManager

# Output JSON path for frontend
DOCS_DIR = Path(PROJECT_ROOT) / "docs"
DATA_JSON = DOCS_DIR / "data.json"


def get_rss_client():
    """Initialize RSS.app client."""
    api_key = os.getenv("RSS_APP_API_KEY")
    if not api_key:
        return None
    return RssAppClient(api_key=api_key)


def get_inoreader_client():
    """Initialize Inoreader client."""
    app_id = os.getenv("CLIENT_ID_INOREADER")
    app_key = os.getenv("CLIENT_SECRET_INOREADER")
    if not app_id or not app_key:
        return None
    auth_manager = InoreaderAuthManager(app_id, app_key)
    return InoreaderClient(app_id, app_key, auth_manager)


def is_rss_feed(url: str) -> bool:
    """Check if URL is an RSS feed."""
    import requests
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        content_type = resp.headers.get("content-type", "").lower()
        if "xml" in content_type or "rss" in content_type or "atom" in content_type:
            return True
        # Check content for RSS/Atom signatures
        text = resp.text[:1000].lower()
        return "<rss" in text or "<feed" in text or "<channel>" in text
    except Exception:
        return False


def sync_data(db: DBClient):
    """Generate JSON data file for the frontend."""
    DOCS_DIR.mkdir(exist_ok=True)
    
    # Get all data
    users = db.get_all_users(active_only=False)
    topics = db.get_all_topics()
    sources = db.get_all_sources(active_only=False)
    countries = db.get_all_countries()
    
    # Build users with topics
    users_data = []
    for u in users:
        user_topics = db.get_user_topics(u.user_id)
        users_data.append({
            "user_id": u.user_id,
            "name": u.name,
            "email": u.email,
            "is_active": u.is_active,
            "topic_ids": [t.topic_id for t in user_topics],
            "topic_names": [t.topic_name for t in user_topics],
        })
    
    # Build topics with source count
    topics_data = []
    for t in topics:
        topic_sources = db.get_sources_by_topic_id(t.topic_id)
        topics_data.append({
            "topic_id": t.topic_id,
            "topic_name": t.topic_name,
            "source_count": len(topic_sources),
        })
    
    # Build sources
    sources_data = []
    for s in sources:
        sources_data.append({
            "source_id": s.source_id,
            "source_name": s.source_name,
            "feed_url": s.feed_url,
            "country_code": s.country_code,
            "is_active": s.is_active,
        })
    
    data = {
        "users": users_data,
        "topics": topics_data,
        "sources": sources_data,
        "countries": countries,
    }
    
    DATA_JSON.write_text(json.dumps(data, indent=2))
    print(f"✅ Synced data to {DATA_JSON}")


def add_user(db: DBClient, name: str, email: str, topic_ids: list):
    """Add a new user."""
    with db.connection() as conn:
        # Check if exists
        cursor = conn.execute("SELECT user_id FROM Users WHERE email = ?", (email,))
        if cursor.fetchone():
            print(f"❌ User with email {email} already exists")
            return False
        
        cursor = conn.execute(
            "INSERT INTO Users (name, email) VALUES (?, ?) RETURNING user_id",
            (name, email)
        )
        user_id = cursor.fetchone()[0]
        
        for tid in topic_ids:
            conn.execute(
                "INSERT INTO User_Topics (user_id, topic_id) VALUES (?, ?)",
                (user_id, int(tid))
            )
    
    db.upload_to_gcs()
    print(f"✅ Added user: {name} ({email})")
    return True


def delete_user(db: DBClient, user_id: int):
    """Delete a user."""
    with db.connection() as conn:
        conn.execute("DELETE FROM User_Topics WHERE user_id = ?", (user_id,))
        cursor = conn.execute("DELETE FROM Users WHERE user_id = ?", (user_id,))
        if cursor.rowcount == 0:
            print(f"❌ User {user_id} not found")
            return False
    
    db.upload_to_gcs()
    print(f"✅ Deleted user {user_id}")
    return True


def add_topic(db: DBClient, topic_name: str):
    """Add a new topic."""
    existing = db.get_topic_by_name(topic_name)
    if existing:
        print(f"❌ Topic '{topic_name}' already exists")
        return False
    
    topic_id = db.add_topic(topic_name)
    db.upload_to_gcs()
    print(f"✅ Added topic: {topic_name} (ID: {topic_id})")
    return True


def delete_topic(db: DBClient, topic_id: int):
    """Delete a topic."""
    with db.connection() as conn:
        conn.execute("DELETE FROM Source_Topics WHERE topic_id = ?", (topic_id,))
        conn.execute("DELETE FROM User_Topics WHERE topic_id = ?", (topic_id,))
        cursor = conn.execute("DELETE FROM Topics WHERE topic_id = ?", (topic_id,))
        if cursor.rowcount == 0:
            print(f"❌ Topic {topic_id} not found")
            return False
    
    db.upload_to_gcs()
    print(f"✅ Deleted topic {topic_id}")
    return True


def add_source(db: DBClient, source_name: str, url: str, country_code: str, topic_ids: list):
    """Add a new source. Creates RSS feed if needed, subscribes in Inoreader."""
    feed_url = url
    inoreader_stream_id = ""
    
    # Check if URL is already an RSS feed
    print(f"   Checking if URL is RSS feed: {url}")
    if not is_rss_feed(url):
        print("   Not an RSS feed. Creating via RSS.app...")
        rss_client = get_rss_client()
        if rss_client:
            try:
                feed_response = rss_client.create_feed_sync(url)
                if feed_response and feed_response.feed_url:
                    feed_url = feed_response.feed_url
                    print(f"   ✅ Created RSS feed: {feed_url}")
                else:
                    print("   ⚠ RSS.app couldn't create feed, using original URL")
            except Exception as e:
                print(f"   ⚠ RSS.app error: {e}")
        else:
            print("   ⚠ RSS_APP_API_KEY not set, using original URL")
    else:
        print("   ✅ URL is already an RSS feed")
    
    # Subscribe in Inoreader
    print("   Subscribing in Inoreader...")
    inoreader = get_inoreader_client()
    if inoreader:
        try:
            import asyncio
            async def subscribe():
                async with inoreader:
                    result = await inoreader.subscribe_to_feed(feed_url, source_name)
                    return result
            
            result = asyncio.run(subscribe())
            if result:
                inoreader_stream_id = f"feed/{feed_url}"
                print(f"   ✅ Subscribed in Inoreader")
            else:
                print("   ⚠ Inoreader subscription returned no result")
        except Exception as e:
            print(f"   ⚠ Inoreader error: {e}")
    else:
        print("   ⚠ Inoreader credentials not set")
    
    # Add to database
    topic_id_list = [int(t) for t in topic_ids] if topic_ids else []
    source_id = db.add_source(
        source_name=source_name,
        inoreader_stream_id=inoreader_stream_id,
        feed_url=feed_url,
        country_code=country_code,
        topic_ids=topic_id_list,
    )
    db.upload_to_gcs()
    print(f"✅ Added source: {source_name} (ID: {source_id})")
    return True


def delete_source(db: DBClient, source_id: int):
    """Delete a source."""
    with db.connection() as conn:
        conn.execute("DELETE FROM Source_Topics WHERE source_id = ?", (source_id,))
        cursor = conn.execute("DELETE FROM Sources WHERE source_id = ?", (source_id,))
        if cursor.rowcount == 0:
            print(f"❌ Source {source_id} not found")
            return False
    
    db.upload_to_gcs()
    print(f"✅ Deleted source {source_id}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Admin actions for Regulatory Intelligence")
    parser.add_argument("action", choices=[
        "sync", "add-user", "delete-user", "add-topic", "delete-topic", "add-source", "delete-source"
    ])
    parser.add_argument("--name", help="Name for user/topic/source")
    parser.add_argument("--email", help="Email for user")
    parser.add_argument("--url", help="URL for source")
    parser.add_argument("--country", default="US", help="Country code for source")
    parser.add_argument("--topics", default="", help="Comma-separated topic IDs")
    parser.add_argument("--user-id", type=int, help="User ID for delete")
    parser.add_argument("--topic-id", type=int, help="Topic ID for delete")
    parser.add_argument("--source-id", type=int, help="Source ID for delete")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print(f"🔧 ADMIN ACTION: {args.action}")
    print("=" * 60)
    
    # Initialize DB
    print("\n[Init] Loading database from GCS...")
    db = DBClient(auto_sync=True)
    
    topic_ids = [t.strip() for t in args.topics.split(",") if t.strip()]
    
    success = False
    if args.action == "sync":
        sync_data(db)
        success = True
    elif args.action == "add-user":
        if not args.name or not args.email:
            print("❌ --name and --email required")
        else:
            success = add_user(db, args.name, args.email, topic_ids)
    elif args.action == "delete-user":
        if not args.user_id:
            print("❌ --user-id required")
        else:
            success = delete_user(db, args.user_id)
    elif args.action == "add-topic":
        if not args.name:
            print("❌ --name required")
        else:
            success = add_topic(db, args.name)
    elif args.action == "delete-topic":
        if not args.topic_id:
            print("❌ --topic-id required")
        else:
            success = delete_topic(db, args.topic_id)
    elif args.action == "add-source":
        if not args.name or not args.url:
            print("❌ --name and --url required")
        else:
            success = add_source(db, args.name, args.url, args.country, topic_ids)
    elif args.action == "delete-source":
        if not args.source_id:
            print("❌ --source-id required")
        else:
            success = delete_source(db, args.source_id)
    
    # Always sync data after changes
    if success and args.action != "sync":
        print("\n[Sync] Updating frontend data...")
        sync_data(db)
    
    print("\n✅ Done!")


if __name__ == "__main__":
    main()
