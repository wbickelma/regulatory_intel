"""
Display Users table as a pandas DataFrame.

Usage:
    python scripts/show_users.py
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

import pandas as pd
from clients.db_client import DBClient


def main():
    db = DBClient(auto_sync=True)
    
    with db.connection() as conn:
        # Users with their subscribed topic count
        df = pd.read_sql_query("""
            SELECT 
                u.user_id,
                u.name,
                u.email,
                u.is_active,
                COUNT(ut.topic_id) as subscribed_topics
            FROM Users u
            LEFT JOIN User_Topics ut ON u.user_id = ut.user_id
            GROUP BY u.user_id
            ORDER BY u.name
        """, conn)
    
    print("\n📧 USERS TABLE")
    print("=" * 80)
    print(df.to_string(index=False))
    print()


if __name__ == "__main__":
    main()
