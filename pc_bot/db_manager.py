"""
db_manager.py - Centralized database operations for the Income Expense Tracker
"""
import sqlite3
import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paths
DB_PATH = Path(__file__).resolve().parent.parent / "db" / "expenses.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)  # Ensure db directory exists
EXPORT_DIR = Path(__file__).resolve().parent.parent / "cloud_bot"

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
def add_category(name: str, category_type: str = "expense", emoji: str = None) -> int:
    """Add a new category to the database.

    Args:
        name: Category name (e.g., 'Groceries').
        category_type: Either 'income' or 'expense'. Defaults to 'expense'.
        emoji: Optional emoji representation.

    Returns:
        int: ID of the newly created category.

    Raises:
        ValueError: If ``category_type`` is not 'income' or 'expense'.
        sqlite3.IntegrityError: If the category name already exists.
    """
    normalized_type = category_type.strip().lower()
    if normalized_type not in {"income", "expense"}:
        raise ValueError("category_type must be either 'income' or 'expense'")

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO categories (name, type, emoji) VALUES (?, ?, ?)",
            (name, normalized_type, emoji)
        )
        conn.commit()

        category_id = cursor.lastrowid
        logger.info(f"Added category '{name}' with ID {category_id}")
        return category_id

    except sqlite3.Error as e:
        logger.error(f"Error adding category '{name}': {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            close_connection(conn)

def get_category(category_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a category by ID."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, type, emoji FROM categories WHERE id = ?",
            (category_id,)
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "type": row[2],
                "emoji": row[3],
            }
        return None
    except sqlite3.Error as e:
        logger.error(f"Error fetching category {category_id}: {e}")
        return None
    finally:
        if conn:
            close_connection(conn)


def get_category_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Retrieve a category by its name."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, type, emoji FROM categories WHERE name = ?",
            (name,)
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "type": row[2],
                "emoji": row[3],
            }
        return None
    except sqlite3.Error as e:
        logger.error(f"Error fetching category '{name}': {e}")
        return None
    finally:
        if conn:
            close_connection(conn)


def update_category(category_id: int, **updates) -> bool:
    """Update category fields (name, type, emoji)."""
    if not updates:
        logger.warning("No updates provided for category")
        return False

    set_parts: List[str] = []
    values: List[Any] = []

    for field, value in updates.items():
        if field == "type":
            normalized = str(value).strip().lower()
            if normalized not in {"income", "expense"}:
                logger.warning("Invalid category type provided")
                continue
            set_parts.append("type = ?")
            values.append(normalized)
        elif field in {"name", "emoji"}:
            set_parts.append(f"{field} = ?")
            values.append(value)
        else:
            logger.warning(f"Ignoring invalid category field '{field}'")

    if not set_parts:
        logger.warning("No valid category fields to update")
        return False

    values.append(category_id)

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE categories SET {', '.join(set_parts)} WHERE id = ?",
            values,
        )
        conn.commit()
        if cursor.rowcount:
            logger.info(f"Updated category {category_id}")
            return True
        logger.warning(f"No category found with ID {category_id}")
        return False
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Error updating category {category_id}: {e}")
        return False
    finally:
        if conn:
            close_connection(conn)


def delete_category(category_id: int) -> bool:
    """Delete a category if no transactions reference it."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE category_id = ?",
            (category_id,)
        )
        in_use = cursor.fetchone()[0]
        if in_use:
            logger.warning(
                f"Cannot delete category {category_id} because it is used in {in_use} transactions"
            )
            return False

        cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        conn.commit()
        if cursor.rowcount:
            logger.info(f"Deleted category {category_id}")
            return True
        logger.warning(f"No category found with ID {category_id}")
        return False
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Error deleting category {category_id}: {e}")
        return False
    finally:
        if conn:
            close_connection(conn)


def list_categories() -> List[Dict[str, Any]]:
    """List all categories."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, type, emoji FROM categories ORDER BY type, name"
        )
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "name": row[1],
                "type": row[2],
                "emoji": row[3],
            }
            for row in rows
        ]
    except sqlite3.Error as e:
        logger.error(f"Error listing categories: {e}")
        return []
    finally:
        if conn:
            close_connection(conn)

# ======================
# Transaction Management
# ======================
def add_transaction(
    account_id: int,
    amount: float,
    txn_type: str,
    date: str,
    category_id: Optional[int] = None,
    description: str = "",
    notes: str = "",
    is_recurring: bool = False,
) -> int:
    """Insert a new transaction row."""
    normalized_type = txn_type.strip().lower()
    if normalized_type not in {"income", "expense", "transfer"}:
        raise ValueError("txn_type must be 'income', 'expense', or 'transfer'")

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO transactions
            (account_id, category_id, amount, type, date, description, notes, is_recurring)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account_id,
                category_id,
                float(amount),
                normalized_type,
                date,
                description,
                notes,
                1 if is_recurring else 0,
            ),
        )
        conn.commit()
        txn_id = cursor.lastrowid
        logger.info(f"Added transaction {txn_id} ({normalized_type})")
        return txn_id
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Error adding transaction: {e}")
        raise
    finally:
        if conn:
            close_connection(conn)


def get_transaction(transaction_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a transaction by ID."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, account_id, category_id, amount, type, date, description, notes, is_recurring
            FROM transactions
            WHERE id = ?
            """,
            (transaction_id,)
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "account_id": row[1],
                "category_id": row[2],
                "amount": row[3],
                "type": row[4],
                "date": row[5],
                "description": row[6],
                "notes": row[7],
                "is_recurring": bool(row[8]),
            }
        return None
    except sqlite3.Error as e:
        logger.error(f"Error fetching transaction {transaction_id}: {e}")
        return None
    finally:
        if conn:
            close_connection(conn)


def update_transaction(transaction_id: int, **updates) -> bool:
    """Update allowed transaction fields."""
    if not updates:
        logger.warning("No updates supplied for transaction")
        return False

    allowed_fields = {
        "account_id",
        "category_id",
        "amount",
        "type",
        "date",
        "description",
        "notes",
        "is_recurring",
    }

    set_parts: List[str] = []
    values: List[Any] = []

    for field, value in updates.items():
        if field not in allowed_fields:
            logger.warning(f"Ignoring invalid transaction field '{field}'")
            continue
        if field == "type":
            normalized = str(value).strip().lower()
            if normalized not in {"income", "expense", "transfer"}:
                logger.warning("Invalid transaction type provided")
                continue
            set_parts.append("type = ?")
            values.append(normalized)
        elif field == "amount":
            set_parts.append("amount = ?")
            values.append(float(value))
        elif field == "is_recurring":
            set_parts.append("is_recurring = ?")
            values.append(1 if value else 0)
        else:
            set_parts.append(f"{field} = ?")
            values.append(value)

    if not set_parts:
        logger.warning("No valid transaction fields to update")
        return False

    values.append(transaction_id)

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE transactions SET {', '.join(set_parts)} WHERE id = ?",
            values,
        )
        conn.commit()
        if cursor.rowcount:
            logger.info(f"Updated transaction {transaction_id}")
            return True
        logger.warning(f"No transaction found with ID {transaction_id}")
        return False
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Error updating transaction {transaction_id}: {e}")
        return False
    finally:
        if conn:
            close_connection(conn)


def delete_transaction(transaction_id: int) -> bool:
    """Delete a transaction if it is not referenced by transfers."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*) FROM transfers
            WHERE from_transaction_id = ? OR to_transaction_id = ?
            """,
            (transaction_id, transaction_id)
        )
        linked = cursor.fetchone()[0]
        if linked:
            logger.warning(
                f"Cannot delete transaction {transaction_id}; referenced in {linked} transfer record(s)"
            )
            return False

        cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        conn.commit()
        if cursor.rowcount:
            logger.info(f"Deleted transaction {transaction_id}")
            return True
        logger.warning(f"No transaction found with ID {transaction_id}")
        return False
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Error deleting transaction {transaction_id}: {e}")
        return False
    finally:
        if conn:
            close_connection(conn)


def list_transactions(
    account_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Return a list of transactions filtered by optional parameters."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        conditions: List[str] = []
        params: List[Any] = []

        if account_id is not None:
            conditions.append("account_id = ?")
            params.append(account_id)
        if start_date is not None:
            conditions.append("date >= ?")
            params.append(start_date)
        if end_date is not None:
            conditions.append("date <= ?")
            params.append(end_date)

        where_clause = ""
        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)

        query = (
            "SELECT id, account_id, category_id, amount, type, date, description, notes, is_recurring "
            "FROM transactions"
            f"{where_clause} "
            "ORDER BY date DESC, id DESC "
            "LIMIT ?"
        )
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "account_id": row[1],
                "category_id": row[2],
                "amount": row[3],
                "type": row[4],
                "date": row[5],
                "description": row[6],
                "notes": row[7],
                "is_recurring": bool(row[8]),
            }
            for row in rows
        ]
    except sqlite3.Error as e:
        logger.error(f"Error listing transactions: {e}")
        return []
    finally:
        if conn:
            close_connection(conn)

# ======================
# Transfer Management
# ======================
def add_transfer(
    from_account_id: int,
    to_account_id: int,
    amount: float,
    date: str,
    description: str = "",
    notes: str = "",
) -> Tuple[int, int, int]:
    """Create a paired debit/credit transaction and link them in transfers."""

    if amount <= 0:
        raise ValueError("Transfer amount must be positive")

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Debit from source account (negative amount)
        cursor.execute(
            """
            INSERT INTO transactions
            (account_id, category_id, amount, type, date, description, notes, is_recurring)
            VALUES (?, NULL, ?, 'transfer', ?, ?, ?, 0)
            """,
            (
                from_account_id,
                -abs(float(amount)),
                date,
                description,
                notes,
            ),
        )
        debit_id = cursor.lastrowid

        # Credit to destination account (positive amount)
        cursor.execute(
            """
            INSERT INTO transactions
            (account_id, category_id, amount, type, date, description, notes, is_recurring)
            VALUES (?, NULL, ?, 'transfer', ?, ?, ?, 0)
            """,
            (
                to_account_id,
                abs(float(amount)),
                date,
                description,
                notes,
            ),
        )
        credit_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO transfers (from_transaction_id, to_transaction_id)
            VALUES (?, ?)
            """,
            (debit_id, credit_id),
        )
        transfer_id = cursor.lastrowid

        conn.commit()
        logger.info(
            f"Created transfer {transfer_id}: debit {debit_id} -> credit {credit_id} ({amount})"
        )
        return transfer_id, debit_id, credit_id
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Error creating transfer: {e}")
        raise
    finally:
        if conn:
            close_connection(conn)


def get_transfer(transfer_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a transfer record with its linked transactions."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, from_transaction_id, to_transaction_id
            FROM transfers
            WHERE id = ?
            """,
            (transfer_id,)
        )
        link_row = cursor.fetchone()
        if not link_row:
            return None

        result = {
            "id": link_row[0],
            "from_transaction": get_transaction(link_row[1]),
            "to_transaction": get_transaction(link_row[2]),
        }
        return result
    except sqlite3.Error as e:
        logger.error(f"Error fetching transfer {transfer_id}: {e}")
        return None
    finally:
        if conn:
            close_connection(conn)


def list_transfers(
    account_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """List transfers with optional filters."""

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        conditions: List[str] = []
        params: List[Any] = []

        if account_id is not None:
            conditions.append(
                "(ft.account_id = ? OR tt.account_id = ?)"
            )
            params.extend([account_id, account_id])
        if start_date is not None:
            conditions.append("ft.date >= ?")
            params.append(start_date)
        if end_date is not None:
            conditions.append("ft.date <= ?")
            params.append(end_date)

        where_clause = ""
        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)

        query = (
            "SELECT tr.id, tr.from_transaction_id, tr.to_transaction_id "
            "FROM transfers tr "
            "JOIN transactions ft ON ft.id = tr.from_transaction_id "
            "JOIN transactions tt ON tt.id = tr.to_transaction_id "
            f"{where_clause} "
            "ORDER BY ft.date DESC, tr.id DESC "
            "LIMIT ?"
        )
        params.append(limit)

        cursor.execute(query, params)
        transfers = []
        for row in cursor.fetchall():
            transfers.append(
                {
                    "id": row[0],
                    "from_transaction": get_transaction(row[1]),
                    "to_transaction": get_transaction(row[2]),
                }
            )
        return transfers
    except sqlite3.Error as e:
        logger.error(f"Error listing transfers: {e}")
        return []
    finally:
        if conn:
            close_connection(conn)

# ======================
# Bill Management
# ======================
def add_bill(
    name: str,
    amount: float,
    due_date: str,
    repeat_freq: str,
    account_id: int,
    is_active: bool = True,
) -> int:
    """Insert a new bill."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO bills (name, amount, due_date, repeat_freq, account_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, float(amount), due_date, repeat_freq, account_id),
        )
        conn.commit()
        bill_id = cursor.lastrowid
        logger.info(f"Added bill '{name}' with ID {bill_id}")
        return bill_id
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Error adding bill '{name}': {e}")
        raise
    finally:
        if conn:
            close_connection(conn)


def get_bill(bill_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a bill by ID."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, amount, due_date, repeat_freq, account_id FROM bills WHERE id = ?",
            (bill_id,),
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "amount": row[2],
                "due_date": row[3],
                "repeat_freq": row[4],
                "account_id": row[5],
            }
        return None
    except sqlite3.Error as e:
        logger.error(f"Error fetching bill {bill_id}: {e}")
        return None
    finally:
        if conn:
            close_connection(conn)


def update_bill(bill_id: int, **updates) -> bool:
    """Update bill fields."""
    if not updates:
        logger.warning("No updates provided for bill")
        return False

    allowed_fields = {"name", "amount", "due_date", "repeat_freq", "account_id"}
    set_parts: List[str] = []
    values: List[Any] = []

    for field, value in updates.items():
        if field not in allowed_fields:
            logger.warning(f"Ignoring invalid bill field '{field}'")
            continue
        set_parts.append(f"{field} = ?")
        if field == "amount":
            values.append(float(value))
        else:
            values.append(value)

    if not set_parts:
        logger.warning("No valid bill fields to update")
        return False

    values.append(bill_id)

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE bills SET {', '.join(set_parts)} WHERE id = ?",
            values,
        )
        conn.commit()
        if cursor.rowcount:
            logger.info(f"Updated bill {bill_id}")
            return True
        logger.warning(f"No bill found with ID {bill_id}")
        return False
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Error updating bill {bill_id}: {e}")
        return False
    finally:
        if conn:
            close_connection(conn)


def delete_bill(bill_id: int) -> bool:
    """Delete a bill."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bills WHERE id = ?", (bill_id,))
        conn.commit()
        if cursor.rowcount:
            logger.info(f"Deleted bill {bill_id}")
            return True
        logger.warning(f"No bill found with ID {bill_id}")
        return False
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Error deleting bill {bill_id}: {e}")
        return False
    finally:
        if conn:
            close_connection(conn)


def list_bills(account_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """List bills optionally filtered by account."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if account_id is None:
            cursor.execute(
                "SELECT id, name, amount, due_date, repeat_freq, account_id FROM bills ORDER BY due_date"
            )
            rows = cursor.fetchall()
        else:
            cursor.execute(
                """
                SELECT id, name, amount, due_date, repeat_freq, account_id
                FROM bills
                WHERE account_id = ?
                ORDER BY due_date
                """,
                (account_id,),
            )
            rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "name": row[1],
                "amount": row[2],
                "due_date": row[3],
                "repeat_freq": row[4],
                "account_id": row[5],
            }
            for row in rows
        ]
    except sqlite3.Error as e:
        logger.error(f"Error listing bills: {e}")
        return []
    finally:
        if conn:
            close_connection(conn)

# ======================
# Subscription Management
# ======================
def add_subscription(
    name: str,
    frequency: str,
    next_due_date: str,
    account_id: int,
    category_id: Optional[int] = None,
    amount: Optional[float] = None,
    active: bool = True,
) -> int:
    """Insert a new subscription."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO subscriptions
            (name, frequency, next_due_date, account_id, category_id, last_posted_date, active)
            VALUES (?, ?, ?, ?, ?, NULL, ?)
            """,
            (name, frequency, next_due_date, account_id, category_id, 1 if active else 0),
        )
        subscription_id = cursor.lastrowid

        # Store amount as a transaction template via notes if provided
        if amount is not None:
            cursor.execute(
                """
                UPDATE subscriptions
                SET last_posted_date = ?
                WHERE id = ?
                """,
                (f"AMOUNT:{amount}", subscription_id),
            )

        conn.commit()
        logger.info(f"Added subscription '{name}' with ID {subscription_id}")
        return subscription_id
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Error adding subscription '{name}': {e}")
        raise
    finally:
        if conn:
            close_connection(conn)


def get_subscription(subscription_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a subscription by ID."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, name, frequency, next_due_date, account_id, category_id, last_posted_date, active
            FROM subscriptions
            WHERE id = ?
            """,
            (subscription_id,),
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "frequency": row[2],
                "next_due_date": row[3],
                "account_id": row[4],
                "category_id": row[5],
                "last_posted_date": row[6],
                "active": bool(row[7]),
            }
        return None
    except sqlite3.Error as e:
        logger.error(f"Error fetching subscription {subscription_id}: {e}")
        return None
    finally:
        if conn:
            close_connection(conn)


def update_subscription(subscription_id: int, **updates) -> bool:
    """Update subscription fields."""
    if not updates:
        logger.warning("No updates provided for subscription")
        return False

    allowed_fields = {
        "name",
        "frequency",
        "next_due_date",
        "account_id",
        "category_id",
        "last_posted_date",
        "active",
    }
    set_parts: List[str] = []
    values: List[Any] = []

    for field, value in updates.items():
        if field not in allowed_fields:
            logger.warning(f"Ignoring invalid subscription field '{field}'")
            continue
        if field == "active":
            set_parts.append("active = ?")
            values.append(1 if value else 0)
        else:
            set_parts.append(f"{field} = ?")
            values.append(value)

    if not set_parts:
        logger.warning("No valid subscription fields to update")
        return False

    values.append(subscription_id)

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE subscriptions SET {', '.join(set_parts)} WHERE id = ?",
            values,
        )
        conn.commit()
        if cursor.rowcount:
            logger.info(f"Updated subscription {subscription_id}")
            return True
        logger.warning(f"No subscription found with ID {subscription_id}")
        return False
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Error updating subscription {subscription_id}: {e}")
        return False
    finally:
        if conn:
            close_connection(conn)


def delete_subscription(subscription_id: int) -> bool:
    """Delete a subscription."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM subscriptions WHERE id = ?", (subscription_id,))
        conn.commit()
        if cursor.rowcount:
            logger.info(f"Deleted subscription {subscription_id}")
            return True
        logger.warning(f"No subscription found with ID {subscription_id}")
        return False
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Error deleting subscription {subscription_id}: {e}")
        return False
    finally:
        if conn:
            close_connection(conn)


def list_subscriptions(active_only: bool = True) -> List[Dict[str, Any]]:
    """List subscriptions, optionally filtering active ones."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if active_only:
            cursor.execute(
                """
                SELECT id, name, frequency, next_due_date, account_id, category_id, last_posted_date, active
                FROM subscriptions
                WHERE active = 1
                ORDER BY next_due_date
                """
            )
        else:
            cursor.execute(
                """
                SELECT id, name, frequency, next_due_date, account_id, category_id, last_posted_date, active
                FROM subscriptions
                ORDER BY next_due_date
                """
            )
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "name": row[1],
                "frequency": row[2],
                "next_due_date": row[3],
                "account_id": row[4],
                "category_id": row[5],
                "last_posted_date": row[6],
                "active": bool(row[7]),
            }
            for row in rows
        ]
    except sqlite3.Error as e:
        logger.error(f"Error listing subscriptions: {e}")
        return []
    finally:
        if conn:
            close_connection(conn)

# ======================
# Helper Functions
# ======================
def export_to_json(data_type: str) -> Path:
    """Export selected table contents to JSON under `cloud_bot/`.

    Args:
        data_type: One of 'accounts', 'categories', 'bills', 'subscriptions'.

    Returns:
        Path to the exported JSON file.
    """

    export_map = {
        "accounts": (
            "SELECT id, name, type, virtual_balance AS balance, active FROM accounts ORDER BY name",
            "accounts.json",
        ),
        "categories": (
            "SELECT id, name, type, COALESCE(emoji, '') AS emoji FROM categories ORDER BY type, name",
            "categories.json",
        ),
        "bills": (
            "SELECT id, name, amount, due_date, repeat_freq, account_id FROM bills ORDER BY due_date",
            "bills.json",
        ),
        "subscriptions": (
            "SELECT id, name, frequency, next_due_date, account_id, category_id, last_posted_date, active FROM subscriptions ORDER BY next_due_date",
            "subscriptions.json",
        ),
    }

    key = data_type.lower()
    if key not in export_map:
        raise ValueError("Unsupported export data_type")

    query, filename = export_map[key]
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        data = [dict(zip(columns, row)) for row in rows]

        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = EXPORT_DIR / filename
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported {len(data)} {key} record(s) to {output_path}")
        return output_path
    except sqlite3.Error as e:
        logger.error(f"Error exporting {key}: {e}")
        raise
    finally:
        if conn:
            close_connection(conn)
if __name__ == "__main__":
    print("Database manager loaded successfully.")
    print("You can now use account management functions.")