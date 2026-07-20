import os
import sqlite3

db_path = "C:\\Users\\gabri\\AppData\\Local\\LUCIFEX\\state.db"

print(f"Checking database: {db_path}")
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, model, cwd FROM sessions WHERE id LIKE 'e990876f%'")
        rows = cursor.fetchall()
        print(f"Session rows (prefix match): {rows}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
else:
    print("Database file not found!")
