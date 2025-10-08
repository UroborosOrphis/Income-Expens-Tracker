import sqlite3
from pathlib import Path

DB_PATH = Path("db/expenses.db")

def clear_database():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Clear all tables
    cur.execute("DELETE FROM accounts")
    cur.execute("DELETE FROM categories")
    cur.execute("DELETE FROM transactions")
    cur.execute("DELETE FROM transfers")
    cur.execute("DELETE FROM bills")
    cur.execute("DELETE FROM reminder_log")
    cur.execute("DELETE FROM subscriptions")

    # Reset autoincrement counters
    cur.execute("DELETE FROM sqlite_sequence WHERE name='accounts'")
    cur.execute("DELETE FROM sqlite_sequence WHERE name='categories'")
    cur.execute("DELETE FROM sqlite_sequence WHERE name='transactions'")
    cur.execute("DELETE FROM sqlite_sequence WHERE name='transfers'")
    cur.execute("DELETE FROM sqlite_sequence WHERE name='bills'")
    cur.execute("DELETE FROM sqlite_sequence WHERE name='reminder_log'")
    cur.execute("DELETE FROM sqlite_sequence WHERE name='subscriptions'")

    conn.commit()
    conn.close()
    print("✅ Database cleared successfully.")

if __name__ == "__main__":
    clear_database()
