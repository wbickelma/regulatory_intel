"""
Database Engine
===============

SQLAlchemy engine and session management.

Responsibilities:
    - Create and configure the SQLAlchemy async/sync engine
    - Provide a session factory for transactional database access
    - Connection pooling configuration for Cloud SQL
    - Health check / connectivity verification

Usage:
    from db.engine import get_session

    with get_session() as session:
        site = session.query(Site).filter_by(id=1).first()

Dependencies:
    - SQLAlchemy
    - psycopg2 or asyncpg (PostgreSQL driver)
    - config.settings (for DATABASE_URL)

Notes:
    - Uses Cloud SQL Connector in production for secure, IAM-based connections.
    - Connection pool size is configurable via settings.
"""
