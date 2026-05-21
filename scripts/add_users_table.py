"""
Add Users table to the regulatory SQLite database.

Creates the Users and User_Topics tables and seeds with initial users.

Usage:
    python scripts/add_users_table.py
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from clients.db_client import DBClient


def create_users_table(db: DBClient):
    """Create Users and User_Topics tables."""
    with db.connection() as conn:
        # Create Users table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create User_Topics junction table (which topics each user is subscribed to)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS User_Topics (
                user_id INTEGER NOT NULL,
                topic_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, topic_id),
                FOREIGN KEY (user_id) REFERENCES Users(user_id),
                FOREIGN KEY (topic_id) REFERENCES Topics(topic_id)
            )
        """)
        
        print("✅ Created Users and User_Topics tables")


def seed_users(db: DBClient):
    """Add initial users with all topic subscriptions."""
    # Get all topics
    topics = db.get_all_topics()
    topic_ids = [t.topic_id for t in topics]
    
    users = [
        ("Will Bickelmann", "wbickelm@cisco.com"),
        ("Ray Liang", "rayliang@cisco.com"),
    ]
    
    with db.connection() as conn:
        for name, email in users:
            # Insert user (skip if exists)
            cursor = conn.execute(
                "SELECT user_id FROM Users WHERE email = ?",
                (email,)
            )
            row = cursor.fetchone()
            
            if row:
                user_id = row[0]
                print(f"   User already exists: {name} ({email})")
            else:
                cursor = conn.execute(
                    "INSERT INTO Users (name, email) VALUES (?, ?) RETURNING user_id",
                    (name, email)
                )
                user_id = cursor.fetchone()[0]
                print(f"   ✅ Added user: {name} ({email})")
            
            # Subscribe to all topics
            for topic_id in topic_ids:
                conn.execute(
                    "INSERT OR IGNORE INTO User_Topics (user_id, topic_id) VALUES (?, ?)",
                    (user_id, topic_id)
                )
            
            print(f"      Subscribed to {len(topic_ids)} topics")


def main():
    print("=" * 60)
    print("📧 ADD USERS TABLE")
    print("=" * 60)
    
    print("\n[1/4] Downloading database from GCS...")
    db = DBClient(auto_sync=True)
    
    print("\n[2/4] Creating tables...")
    create_users_table(db)
    
    print("\n[3/4] Seeding users...")
    seed_users(db)
    
    print("\n[4/4] Uploading database to GCS...")
    db.upload_to_gcs()
    print("✅ Database uploaded")
    
    # Show stats
    print("\n" + "=" * 60)
    print("📊 DATABASE STATS")
    print("=" * 60)
    stats = db.get_stats()
    for table, count in stats.items():
        print(f"   {table}: {count} rows")
    
    # Show users table
    with db.connection() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM Users")
        print(f"   Users: {cursor.fetchone()[0]} rows")
        cursor = conn.execute("SELECT COUNT(*) FROM User_Topics")
        print(f"   User_Topics: {cursor.fetchone()[0]} rows")
    
    print("\n✅ Done!")


if __name__ == "__main__":
    main()
