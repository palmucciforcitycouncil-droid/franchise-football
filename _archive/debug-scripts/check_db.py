import sqlite3

conn = sqlite3.connect('db/ff.db')
cursor = conn.cursor()

# Get all table names
tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Tables in database:")
for table in tables:
    print(f"  - {table[0]}")

# Check if team table exists and has data
if any('team' in str(t).lower() for t in tables):
    cursor.execute("SELECT COUNT(*) FROM team")
    count = cursor.fetchone()[0]
    print(f"\nTeams in database: {count}")

conn.close()
