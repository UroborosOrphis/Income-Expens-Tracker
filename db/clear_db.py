import sqlite3
from pathlib import Path

DB_PATH = Path("db/expenses.db")

def clear_database():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Clear all tables
    cur.execute("DELETE FROM accounts")
    cur.execute("DELETE FROM transactions")
    cur.execute("DELETE FROM bills")

    # Reset autoincrement counters
    cur.execute("DELETE FROM sqlite_sequence WHERE name='accounts'")
    cur.execute("DELETE FROM sqlite_sequence WHERE name='transactions'")
    cur.execute("DELETE FROM sqlite_sequence WHERE name='bills'")

    conn.commit()
    conn.close()
    print("✅ Database cleared successfully.")

if __name__ == "__main__":
    clear_database()
