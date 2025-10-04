# init_db.py
import sqlite3
from pathlib import Path

DB_PATH = Path("db/expenses.db")
SCHEMA_PATH = Path("db/schema.sql")

def init_db():
    # Make sure db folder exists
    DB_PATH.parent.mkdir(exist_ok=True)

    # Read schema.sql
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    # Connect to database (creates file if it doesn't exist)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Execute schema
    cursor.executescript(schema_sql)
    conn.commit()
    conn.close()

    print(f"Database initialized at: {DB_PATH.resolve()}")

if __name__ == "__main__":
    init_db()
