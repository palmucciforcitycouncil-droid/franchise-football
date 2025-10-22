#!/usr/bin/env python3
"""
CREATE STATS TABLES
Create the stats database tables.
"""

import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.core.db import create_db_and_tables

def main():
    print("Creating stats database tables...")
    try:
        create_db_and_tables()
        print("SUCCESS: Stats tables created successfully!")
    except Exception as e:
        print(f"ERROR: Failed to create stats tables: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
