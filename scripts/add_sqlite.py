"""
SQLite database management with GCS storage.

Usage:
    python scripts/add_sqlite.py init      # Create DB from CSVs and upload to GCS
    python scripts/add_sqlite.py download  # Download DB from GCS
    python scripts/add_sqlite.py upload    # Upload local DB to GCS
"""
import csv
import sqlite3
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from clients.gcs_client import GCSClient

# --- CONFIGURATION ---
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
LOCAL_DB_PATH = os.path.join(DATA_DIR, "regulatory.db")
GCS_DB_BLOB = "regulatory.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS Countries (
    country_code TEXT PRIMARY KEY,
    country_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Topics (
    topic_id INTEGER PRIMARY KEY,
    topic_name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS Sources (
    source_id INTEGER PRIMARY KEY,
    source_name TEXT NOT NULL,
    country_code TEXT,
    inoreader_stream_id TEXT UNIQUE NOT NULL,
    feed_url TEXT,
    last_fetched_at TEXT,
    is_active INTEGER DEFAULT 1,
    FOREIGN KEY (country_code) REFERENCES Countries(country_code)
);

CREATE TABLE IF NOT EXISTS Source_Topics (
    source_id INTEGER,
    topic_id INTEGER,
    PRIMARY KEY (source_id, topic_id),
    FOREIGN KEY (source_id) REFERENCES Sources(source_id),
    FOREIGN KEY (topic_id) REFERENCES Topics(topic_id)
);
"""


def init_db_from_csvs():
    """Create SQLite DB from CSV files and upload to GCS."""
    print(f"Creating database at {LOCAL_DB_PATH}...")
    
    # Remove existing DB if present
    if os.path.exists(LOCAL_DB_PATH):
        os.remove(LOCAL_DB_PATH)
    
    conn = sqlite3.connect(LOCAL_DB_PATH)
    cursor = conn.cursor()
    
    # Create tables
    print("Initializing schema...")
    cursor.executescript(SCHEMA_SQL)
    
    # Load Countries
    print("Loading Countries...")
    csv_path = os.path.join(DATA_DIR, 'countries.csv')
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)
        cursor.executemany(
            "INSERT OR IGNORE INTO Countries (country_code, country_name) VALUES (?, ?)",
            list(reader)
        )
        
    # Load Topics
    print("Loading Topics...")
    csv_path = os.path.join(DATA_DIR, 'topics.csv')
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)
        cursor.executemany(
            "INSERT OR IGNORE INTO Topics (topic_id, topic_name) VALUES (?, ?)",
            list(reader)
        )
        
    # Load Sources
    print("Loading Sources...")
    csv_path = os.path.join(DATA_DIR, 'sources.csv')
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)
        source_data = []
        for row in reader:
            last_fetched = None if not row[5] else row[5]
            is_active = 1 if row[6] == 'True' else 0
            source_data.append((row[0], row[1], row[2], row[3], row[4], last_fetched, is_active))
        
        cursor.executemany(
            """INSERT OR IGNORE INTO Sources 
               (source_id, source_name, country_code, inoreader_stream_id, feed_url, last_fetched_at, is_active) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            source_data
        )

    # Load Source_Topics
    print("Loading Source-Topic mappings...")
    csv_path = os.path.join(DATA_DIR, 'source_topics.csv')
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)
        cursor.executemany(
            "INSERT OR IGNORE INTO Source_Topics (source_id, topic_id) VALUES (?, ?)",
            list(reader)
        )

    conn.commit()
    conn.close()
    print(f"✅ Database created: {LOCAL_DB_PATH}")
    
    # Upload to GCS
    upload_to_gcs()


def download_from_gcs():
    """Download SQLite DB from GCS."""
    print("Downloading database from GCS...")
    gcs = GCSClient()
    
    blob = gcs._bucket.blob(GCS_DB_BLOB)
    if not blob.exists():
        print(f"❌ Database not found in GCS: {GCS_DB_BLOB}")
        return False
    
    blob.download_to_filename(LOCAL_DB_PATH)
    print(f"✅ Downloaded to {LOCAL_DB_PATH}")
    return True


def upload_to_gcs():
    """Upload local SQLite DB to GCS."""
    if not os.path.exists(LOCAL_DB_PATH):
        print(f"❌ Local database not found: {LOCAL_DB_PATH}")
        return False
    
    print("Uploading database to GCS...")
    gcs = GCSClient()
    
    blob = gcs._bucket.blob(GCS_DB_BLOB)
    blob.upload_from_filename(LOCAL_DB_PATH)
    print(f"✅ Uploaded to gs://{gcs.bucket_name}/{GCS_DB_BLOB}")
    return True


def delete_local():
    """Delete local copy of database."""
    if os.path.exists(LOCAL_DB_PATH):
        os.remove(LOCAL_DB_PATH)
        print(f"✅ Deleted local database: {LOCAL_DB_PATH}")


def show_stats():
    """Show database statistics."""
    if not os.path.exists(LOCAL_DB_PATH):
        print("❌ Local database not found. Run 'download' first.")
        return
    
    conn = sqlite3.connect(LOCAL_DB_PATH)
    cursor = conn.cursor()
    
    tables = ['Countries', 'Topics', 'Sources', 'Source_Topics']
    print("\n📊 Database Statistics:")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"   {table}: {count} rows")
    
    conn.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SQLite DB management with GCS")
    parser.add_argument("command", choices=["init", "download", "upload", "delete", "stats"],
                        help="Command to run")
    args = parser.parse_args()
    
    if args.command == "init":
        init_db_from_csvs()
    elif args.command == "download":
        download_from_gcs()
    elif args.command == "upload":
        upload_to_gcs()
    elif args.command == "delete":
        delete_local()
    elif args.command == "stats":
        show_stats()