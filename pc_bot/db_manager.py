"""
db_manager.py - Centralized database operations for the Income Expense Tracker
"""
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paths
DB_PATH = Path(__file__).resolve().parent.parent / "db" / "expenses.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)  # Ensure db directory exists

# ======================
# Database Connection
# ======================

def get_connection() -> sqlite3.Connection:
    """Get a database connection.
    
    Returns:
        sqlite3.Connection: Database connection object
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        # Enable foreign key support
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Error connecting to database: {e}")
        raise

def close_connection(conn: sqlite3.Connection) -> None:
    """Close the database connection.
    
    Args:
        conn: Database connection to close
    """
    if conn:
        conn.close()

# ======================
# Account Management
# ======================

def add_account(name: str, account_type: str, emoji: str = None) -> int:
    """Add a new account to the database.

    Args:
        name: Name of the account (e.g., 'Cash Wallet')
        account_type: Type of account (e.g., 'wallet', 'bank', 'credit_card')
        emoji: Emoji for the account (optional) - Note: stored in notes/description

    Returns:
        int: ID of the newly created account

    Raises:
        sqlite3.IntegrityError: If account name already exists
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Schema only has: id, name, type, virtual_balance, active
        # We'll use virtual_balance as the balance field
        cursor.execute(
            "INSERT INTO accounts (name, type, virtual_balance, active) VALUES (?, ?, 0, 1)",
            (name, account_type)
        )
        conn.commit()

        account_id = cursor.lastrowid
        logger.info(f"Added account '{name}' with ID {account_id}")
        return account_id

    except sqlite3.Error as e:
        logger.error(f"Error adding account '{name}': {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            close_connection(conn)

def get_account(account_id: int) -> Optional[Dict[str, Any]]:
    """Get an account by ID.

    Args:
        account_id: ID of the account to retrieve

    Returns:
        Dict containing account information or None if not found
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Schema: id, name, type, virtual_balance, active
        cursor.execute(
            "SELECT id, name, type, virtual_balance, active FROM accounts WHERE id = ?",
            (account_id,)
        )

        row = cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'name': row[1],
                'type': row[2],
                'balance': row[3],  # virtual_balance from schema
                'active': row[4]
            }
        return None

    except sqlite3.Error as e:
        logger.error(f"Error getting account with ID {account_id}: {e}")
        return None
    finally:
        if conn:
            close_connection(conn)

def get_account_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Get an account by name.

    Args:
        name: Name of the account to retrieve

    Returns:
        Dict containing account information or None if not found
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Schema: id, name, type, virtual_balance, active
        cursor.execute(
            "SELECT id, name, type, virtual_balance, active FROM accounts WHERE name = ?",
            (name,)
        )

        row = cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'name': row[1],
                'type': row[2],
                'balance': row[3],  # virtual_balance from schema
                'active': row[4]
            }
        return None

    except sqlite3.Error as e:
        logger.error(f"Error getting account '{name}': {e}")
        return None
    finally:
        if conn:
            close_connection(conn)

def update_account(account_id: int, **updates) -> bool:
    """Update an account's information.

    Args:
        account_id: ID of the account to update
        **updates: Keyword arguments for fields to update (name, type, balance, active)

    Returns:
        bool: True if update was successful, False otherwise
    """
    if not updates:
        logger.warning("No updates provided for account update")
        return False

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Build dynamic update query - schema only allows: name, type, virtual_balance, active
        set_clauses = []
        values = []

        for field, value in updates.items():
            if field in ['name', 'type', 'balance', 'active']:
                set_clauses.append(f"{field} = ?" if field != 'balance' else "virtual_balance = ?")
                values.append(value)
            else:
                logger.warning(f"Invalid field '{field}' for account update")

        if not set_clauses:
            logger.warning("No valid fields to update")
            return False

        values.append(account_id)

        query = f"UPDATE accounts SET {', '.join(set_clauses)} WHERE id = ?"

        cursor.execute(query, values)
        conn.commit()

        if cursor.rowcount > 0:
            logger.info(f"Updated account with ID {account_id}")
            return True
        else:
            logger.warning(f"No account found with ID {account_id}")
            return False

    except sqlite3.Error as e:
        logger.error(f"Error updating account with ID {account_id}: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            close_connection(conn)

def delete_account(account_id: int) -> bool:
    """Delete an account from the database.

    Args:
        account_id: ID of the account to delete

    Returns:
        bool: True if deletion was successful, False otherwise
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Check if account has transactions
        cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE account_id = ?",
            (account_id,)
        )
        transaction_count = cursor.fetchone()[0]

        if transaction_count > 0:
            logger.warning(f"Cannot delete account {account_id} - it has {transaction_count} transactions")
            return False

        cursor.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        conn.commit()

        if cursor.rowcount > 0:
            logger.info(f"Deleted account with ID {account_id}")
            return True
        else:
            logger.warning(f"No account found with ID {account_id}")
            return False

    except sqlite3.Error as e:
        logger.error(f"Error deleting account with ID {account_id}: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            close_connection(conn)

def list_accounts() -> List[Dict[str, Any]]:
    """List all accounts in the database.

    Returns:
        List of dictionaries containing account information
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Schema: id, name, type, virtual_balance, active
        cursor.execute(
            "SELECT id, name, type, virtual_balance, active FROM accounts ORDER BY name"
        )

        accounts = []
        for row in cursor.fetchall():
            accounts.append({
                'id': row[0],
                'name': row[1],
                'type': row[2],
                'balance': row[3],  # virtual_balance from schema
                'active': row[4]
            })

        return accounts

    except sqlite3.Error as e:
        logger.error(f"Error listing accounts: {e}")
        return []
    finally:
        if conn:
            close_connection(conn)

def account_exists(name: str) -> bool:
    """Check if an account exists by name.

    Args:
        name: Name of the account to check

    Returns:
        bool: True if account exists, False otherwise
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM accounts WHERE name = ?", (name,))
        count = cursor.fetchone()[0]

        return count > 0

    except sqlite3.Error as e:
        logger.error(f"Error checking account existence for '{name}': {e}")
        return False
    finally:
        if conn:
            close_connection(conn)

# ======================
# Category Management - TODO: Implement all functions
# ======================
# TODO: def add_category(name: str, emoji: str = None, type: str = "expense") -> int
# TODO: def get_category(category_id: int) -> Optional[Dict]
# TODO: def get_category_by_name(name: str) -> Optional[Dict]
# TODO: def update_category(category_id: int, **updates) -> bool
# TODO: def delete_category(category_id: int) -> bool
# TODO: def list_categories() -> List[Dict]

# ======================
# Transaction Management - TODO: Implement all functions
# ======================
# TODO: def add_transaction(account_id: int, amount: float, type: str, date: str, category_id: int = None, description: str = "", notes: str = "", is_recurring: bool = False) -> int
# TODO: def get_transaction(transaction_id: int) -> Optional[Dict]
# TODO: def update_transaction(transaction_id: int, **updates) -> bool
# TODO: def delete_transaction(transaction_id: int) -> bool
# TODO: def list_transactions(account_id: int = None, start_date: str = None, end_date: str = None, limit: int = 100) -> List[Dict]

# ======================
# Transfer Management - TODO: Implement all functions
# ======================
# TODO: def add_transfer(from_account_id: int, to_account_id: int, amount: float, date: str, description: str = "") -> Tuple[int, int]
# TODO: def get_transfer(transfer_id: int) -> Optional[Dict]
# TODO: def list_transfers(account_id: int = None, start_date: str = None, end_date: str = None) -> List[Dict]

# ======================
# Bill Management - TODO: Implement all functions
# ======================
# TODO: def add_bill(name: str, amount: float, due_date: str, account_id: int, repeat_freq: str = "monthly") -> int
# TODO: def get_bill(bill_id: int) -> Optional[Dict]
# TODO: def update_bill(bill_id: int, **updates) -> bool
# TODO: def delete_bill(bill_id: int) -> bool
# TODO: def list_bills(account_id: int = None) -> List[Dict]

# ======================
# Subscription Management - TODO: Implement all functions
# ======================
# TODO: def add_subscription(name: str, amount: float, frequency: str, next_due_date: str, account_id: int, category_id: int = None) -> int
# TODO: def get_subscription(subscription_id: int) -> Optional[Dict]
# TODO: def update_subscription(subscription_id: int, **updates) -> bool
# TODO: def delete_subscription(subscription_id: int) -> bool
# TODO: def list_subscriptions(active_only: bool = True) -> List[Dict]

# ======================
# Helper Functions - TODO: Implement
# ======================
# TODO: def export_to_json(data_type: str) -> str
if __name__ == "__main__":
    print("Database manager loaded successfully.")
    print("You can now use account management functions.")