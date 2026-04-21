"""
API Dependencies
================

Shared FastAPI dependencies injected into route handlers.

Dependencies:
    get_db_session()
        - Yields a SQLAlchemy session from the connection pool
        - Ensures sessions are properly closed after request completes

    verify_api_key()
        - (Optional) Simple authentication middleware if the API
          is exposed publicly without an API Gateway.
"""
