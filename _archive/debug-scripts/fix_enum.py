import sqlite3

conn = sqlite3.connect('db/ff.db')
cursor = conn.cursor()

# Fix the division enum values
cursor.execute("UPDATE team SET div = 'EAST' WHERE div = 'East'")

# Verify the fix
cursor.execute("SELECT id, location_name, div FROM team")
print("Teams after fix:")
for row in cursor.fetchall():
    print(row)

conn.commit()
conn.close()

print("\nEnum values fixed!")
