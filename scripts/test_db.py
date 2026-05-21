"""Test script for DB client - prints all topics."""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from clients.db_client import DBClient

def main():
    print("Connecting to database...")
    db = DBClient()
    
    print("\n📁 All Topics:")
    print("-" * 40)
    for topic in db.get_all_topics():
        sources = db.get_sources_by_topic_id(topic.topic_id)
        print(f"  [{topic.topic_id}] {topic.topic_name} ({len(sources)} sources)")
    
    print("\n" + "-" * 40)
    stats = db.get_stats()
    print(f"Total: {stats['Topics']} topics, {stats['Sources']} sources")

if __name__ == "__main__":
    main()
