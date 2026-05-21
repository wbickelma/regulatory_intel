"""
SQLite database client with GCS sync.

Automatically downloads DB from GCS, performs operations, and optionally syncs back.
"""
import sqlite3
import os
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from contextlib import contextmanager

from dotenv import load_dotenv
load_dotenv()

from clients.gcs_client import GCSClient


@dataclass
class Source:
    source_id: int
    source_name: str
    country_code: str
    inoreader_stream_id: str
    feed_url: str
    last_fetched_at: Optional[str]
    is_active: bool


@dataclass
class Topic:
    topic_id: int
    topic_name: str


@dataclass
class User:
    user_id: int
    name: str
    email: str
    is_active: bool


class DBClient:
    """SQLite database client with GCS storage backend."""
    
    GCS_DB_BLOB = "regulatory.db"
    
    def __init__(self, local_db_path: str = None, auto_sync: bool = True):
        """
        Initialize DB client.
        
        Args:
            local_db_path: Path for local DB file. Defaults to data/regulatory.db
            auto_sync: If True, automatically download DB from GCS on init
        """
        if local_db_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.local_db_path = os.path.join(project_root, "data", "regulatory.db")
        else:
            self.local_db_path = local_db_path
        
        self._gcs = None
        self._conn = None
        
        if auto_sync:
            self.download_from_gcs()
    
    @property
    def gcs(self) -> GCSClient:
        """Lazy-load GCS client."""
        if self._gcs is None:
            self._gcs = GCSClient()
        return self._gcs
    
    @contextmanager
    def connection(self):
        """Context manager for database connection."""
        conn = sqlite3.connect(self.local_db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    # ==================== GCS Operations ====================
    
    def download_from_gcs(self) -> bool:
        """Download database from GCS."""
        blob = self.gcs._bucket.blob(self.GCS_DB_BLOB)
        if not blob.exists():
            print(f"⚠ Database not found in GCS: {self.GCS_DB_BLOB}")
            return False
        
        os.makedirs(os.path.dirname(self.local_db_path), exist_ok=True)
        blob.download_to_filename(self.local_db_path)
        return True
    
    def upload_to_gcs(self) -> bool:
        """Upload database to GCS."""
        if not os.path.exists(self.local_db_path):
            print(f"⚠ Local database not found: {self.local_db_path}")
            return False
        
        blob = self.gcs._bucket.blob(self.GCS_DB_BLOB)
        blob.upload_from_filename(self.local_db_path)
        return True
    
    def delete_local(self):
        """Delete local database file."""
        if os.path.exists(self.local_db_path):
            os.remove(self.local_db_path)
    
    # ==================== Topic Operations ====================
    
    def get_all_topics(self) -> List[Topic]:
        """Get all topics."""
        with self.connection() as conn:
            cursor = conn.execute("SELECT topic_id, topic_name FROM Topics ORDER BY topic_name")
            return [Topic(topic_id=row['topic_id'], topic_name=row['topic_name']) 
                    for row in cursor.fetchall()]
    
    def get_topic_by_name(self, topic_name: str) -> Optional[Topic]:
        """Get a topic by name."""
        with self.connection() as conn:
            cursor = conn.execute(
                "SELECT topic_id, topic_name FROM Topics WHERE topic_name = ?",
                (topic_name,)
            )
            row = cursor.fetchone()
            if row:
                return Topic(topic_id=row['topic_id'], topic_name=row['topic_name'])
            return None
    
    def add_topic(self, topic_name: str) -> int:
        """Add a new topic. Returns topic_id."""
        with self.connection() as conn:
            cursor = conn.execute(
                "INSERT INTO Topics (topic_name) VALUES (?) RETURNING topic_id",
                (topic_name,)
            )
            return cursor.fetchone()[0]
    
    # ==================== Source Operations ====================
    
    def get_sources_by_topic(self, topic_name: str) -> List[Source]:
        """Get all sources (RSS feeds) for a given topic."""
        with self.connection() as conn:
            cursor = conn.execute("""
                SELECT s.source_id, s.source_name, s.country_code, 
                       s.inoreader_stream_id, s.feed_url, s.last_fetched_at, s.is_active
                FROM Sources s
                JOIN Source_Topics st ON s.source_id = st.source_id
                JOIN Topics t ON st.topic_id = t.topic_id
                WHERE t.topic_name = ?
                ORDER BY s.source_name
            """, (topic_name,))
            return [self._row_to_source(row) for row in cursor.fetchall()]
    
    def get_sources_by_topic_id(self, topic_id: int) -> List[Source]:
        """Get all sources for a given topic ID."""
        with self.connection() as conn:
            cursor = conn.execute("""
                SELECT s.source_id, s.source_name, s.country_code, 
                       s.inoreader_stream_id, s.feed_url, s.last_fetched_at, s.is_active
                FROM Sources s
                JOIN Source_Topics st ON s.source_id = st.source_id
                WHERE st.topic_id = ?
                ORDER BY s.source_name
            """, (topic_id,))
            return [self._row_to_source(row) for row in cursor.fetchall()]
    
    def get_all_sources(self, active_only: bool = True) -> List[Source]:
        """Get all sources."""
        with self.connection() as conn:
            query = """
                SELECT source_id, source_name, country_code, 
                       inoreader_stream_id, feed_url, last_fetched_at, is_active
                FROM Sources
            """
            if active_only:
                query += " WHERE is_active = 1"
            query += " ORDER BY source_name"
            
            cursor = conn.execute(query)
            return [self._row_to_source(row) for row in cursor.fetchall()]
    
    def add_source(
        self,
        source_name: str,
        inoreader_stream_id: str,
        feed_url: str,
        country_code: str = "US",
        topic_ids: List[int] = None
    ) -> int:
        """
        Add a new source and optionally link to topics.
        
        Returns the new source_id.
        """
        with self.connection() as conn:
            # Insert source
            cursor = conn.execute("""
                INSERT INTO Sources (source_name, country_code, inoreader_stream_id, feed_url, is_active)
                VALUES (?, ?, ?, ?, 1)
                RETURNING source_id
            """, (source_name, country_code, inoreader_stream_id, feed_url))
            source_id = cursor.fetchone()[0]
            
            # Link to topics
            if topic_ids:
                for topic_id in topic_ids:
                    conn.execute(
                        "INSERT OR IGNORE INTO Source_Topics (source_id, topic_id) VALUES (?, ?)",
                        (source_id, topic_id)
                    )
            
            return source_id
    
    # ==================== Country Operations ====================
    
    def get_all_countries(self) -> List[Dict[str, str]]:
        """Get all countries."""
        with self.connection() as conn:
            cursor = conn.execute("SELECT country_code, country_name FROM Countries ORDER BY country_name")
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== Utility ====================
    
    def _row_to_source(self, row: sqlite3.Row) -> Source:
        """Convert a database row to a Source object."""
        return Source(
            source_id=row['source_id'],
            source_name=row['source_name'],
            country_code=row['country_code'],
            inoreader_stream_id=row['inoreader_stream_id'],
            feed_url=row['feed_url'],
            last_fetched_at=row['last_fetched_at'],
            is_active=bool(row['is_active'])
        )
    
    def get_stats(self) -> Dict[str, int]:
        """Get row counts for all tables."""
        with self.connection() as conn:
            stats = {}
            for table in ['Countries', 'Topics', 'Sources', 'Source_Topics', 'Users', 'User_Topics']:
                try:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[table] = cursor.fetchone()[0]
                except Exception:
                    pass  # Table may not exist yet
            return stats
    
    # ==================== User Operations ====================
    
    def get_all_users(self, active_only: bool = True) -> List[User]:
        """Get all users."""
        with self.connection() as conn:
            query = "SELECT user_id, name, email, is_active FROM Users"
            if active_only:
                query += " WHERE is_active = 1"
            query += " ORDER BY name"
            cursor = conn.execute(query)
            return [User(
                user_id=row['user_id'],
                name=row['name'],
                email=row['email'],
                is_active=bool(row['is_active'])
            ) for row in cursor.fetchall()]
    
    def get_users_by_topic(self, topic_name: str, active_only: bool = True) -> List[User]:
        """Get all users subscribed to a topic."""
        with self.connection() as conn:
            query = """
                SELECT u.user_id, u.name, u.email, u.is_active
                FROM Users u
                JOIN User_Topics ut ON u.user_id = ut.user_id
                JOIN Topics t ON ut.topic_id = t.topic_id
                WHERE t.topic_name = ?
            """
            if active_only:
                query += " AND u.is_active = 1"
            query += " ORDER BY u.name"
            cursor = conn.execute(query, (topic_name,))
            return [User(
                user_id=row['user_id'],
                name=row['name'],
                email=row['email'],
                is_active=bool(row['is_active'])
            ) for row in cursor.fetchall()]
    
    def get_user_topics(self, user_id: int) -> List[Topic]:
        """Get all topics a user is subscribed to."""
        with self.connection() as conn:
            cursor = conn.execute("""
                SELECT t.topic_id, t.topic_name
                FROM Topics t
                JOIN User_Topics ut ON t.topic_id = ut.topic_id
                WHERE ut.user_id = ?
                ORDER BY t.topic_name
            """, (user_id,))
            return [Topic(topic_id=row['topic_id'], topic_name=row['topic_name'])
                    for row in cursor.fetchall()]
