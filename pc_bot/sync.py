import sqlite3
import json
import sys
from pathlib import Path
from datetime import datetime

# ======================
# Configuration & Paths
# ======================

# Determine project root path relative to this script
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Database file location
DB_PATH = PROJECT_ROOT / "db" / "expenses.db"

# Cloud Bot's JSON buffer location
BUFFER_FILE_PATH = PROJECT_ROOT / "cloud_bot" / "expense_buffer.json"


# ======================
# Database Lookup Functions
# ======================

def get_db_connection():
    """Connect to the SQLite database."""
    if not DB_PATH.exists():
        print(f"Error: Database file not found at {DB_PATH}. Please run init_db.py first.")
        sys.exit(1)

    try:
        conn = sqlite3.connect(DB_PATH)
        # Allows accessing columns by name
        conn.row_factory = sqlite3.Row
        # Enforce foreign key constraints
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        sys.exit(1)


def get_account_id(conn, account_name):
    """Retrieves the account_id from the 'accounts' table based on the name."""
    cursor = conn.cursor()
    # Case-insensitive lookup for robustness
    cursor.execute("SELECT id FROM accounts WHERE name = ?", (account_name,))
    result = cursor.fetchone()
    if result:
        return result['id']

    # Fail fast if account is unknown
    raise ValueError(f"CRITICAL: Account '{account_name}' not found in the database. Cannot sync transaction.")


# ======================
# Core Transaction Sync Logic
# ======================

def insert_transaction(conn, transaction):
    """Inserts a single transaction from the buffer into the database."""

    # 1. Look up the required foreign key (account_id)
    try:
        account_id = get_account_id(conn, transaction['account'])
    except ValueError as e:
        print(f"ERROR: {e}")
        return False

        # 2. Type is 'expense' (based on your Cloud Bot design)
    transaction_type = 'expense'

    # 3. Construct the record based on your schema (schema.sql)
    data = (
        account_id,
        transaction['date'],
        transaction['amount'],
        transaction['category'],
        transaction['description'],
        transaction_type,
        transaction['timestamp'],
    )

    # 4. Insert into DB
    try:
        sql = """
              INSERT INTO transactions (account_id, date, amount, category, description, type, created_at)
              VALUES (?, ?, ?, ?, ?, ?, ?) \
              """
        conn.execute(sql, data)
        return True
    except sqlite3.Error as e:
        print(f"Error inserting transaction: {e}")
        return False


def sync_buffer():
    """Reads the JSON buffer, inserts transactions, and clears the buffer."""

    if not BUFFER_FILE_PATH.exists():
        print("Buffer file not found. Nothing to sync.")
        return 0

    try:
        with open(BUFFER_FILE_PATH, 'r', encoding='utf-8') as f:
            buffer_data = json.load(f)
    except json.JSONDecodeError:
        print("Error reading buffer file (invalid JSON). Sync cancelled.")
        return 0

    if not buffer_data:
        print("Buffer is empty. Nothing to sync.")
        return 0

    print(f"Found {len(buffer_data)} new transactions in the buffer.")

    conn = get_db_connection()
    count_synced = 0

    try:
        # Track success for each transaction
        results = [insert_transaction(conn, t) for t in buffer_data]
        count_synced = sum(results)

        # Commit and clear buffer only if *all* transactions were successfully processed
        if count_synced == len(buffer_data):
            conn.commit()

            # Clear the buffer file
            with open(BUFFER_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=2)

            print(f"✅ Successfully synced and committed {count_synced} transactions.")
            print("✅ Buffer file cleared.")
        else:
            conn.rollback()
            # This happens if an account name was not found
            print(
                f"❌ Sync failed for {len(buffer_data) - count_synced} entries. Rolled back changes. Buffer remains untouched.")

    except Exception as e:
        conn.rollback()
        print(f"An unexpected error occurred during sync: {e}")
        print("❌ Database changes rolled back. Buffer remains untouched.")

    finally:
        conn.close()

    return count_synced


# ======================
# Execution
# ======================

if __name__ == "__main__":
    print("--- PC Sync Bot Started ---")
    sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Sync initiated at: {sync_time}")

    synced_count = sync_buffer()

    print(f"--- PC Sync Bot Finished. Total synced: {synced_count} ---")