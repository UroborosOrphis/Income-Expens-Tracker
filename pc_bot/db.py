import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "db" / "expenses.db"

def get_connection():
    """Open a connection to the database."""
    return sqlite3.connect(DB_PATH)

# ======================
# Accounts
# ======================
def add_account(name: str, acc_type: str, balance: float = 0):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO accounts (name, type, balance) VALUES (?, ?, ?)",
            (name, acc_type, balance),
        )
        conn.commit()

def get_accounts():
    with get_connection() as conn:
        return conn.execute("SELECT id, name, type, balance FROM accounts").fetchall()

# ======================
# Transactions
# ======================
def add_transaction(account_id: int, date: str, amount: float, category: str,
                    description: str, tx_type: str):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO transactions (account_id, date, amount, category, description, type) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (account_id, date, amount, category, description, tx_type),
        )
        conn.commit()

def get_transactions(limit: int = 20):
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, account_id, date, amount, category, description, type "
            "FROM transactions ORDER BY date DESC LIMIT ?", (limit,)
        ).fetchall()

# ======================
# Bills
# ======================
def add_bill(account_id: int, name: str, amount: float, due_date: str,
             pay_from: str = None, pay_until: str = None):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO bills (account_id, name, amount, due_date, pay_from, pay_until) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (account_id, name, amount, due_date, pay_from, pay_until),
        )
        conn.commit()

def get_upcoming_bills(days_ahead: int = 7):
    """Fetch unpaid bills due within X days."""
    with get_connection() as conn:
        return conn.execute(
            """SELECT id, name, amount, due_date, pay_from, pay_until 
               FROM bills 
               WHERE is_paid = 0 
               AND due_date <= date('now', '+' || ? || ' days') 
               ORDER BY due_date""",
            (days_ahead,),
        ).fetchall()

def mark_bill_paid(bill_id: int):
    with get_connection() as conn:
        conn.execute("UPDATE bills SET is_paid = 1 WHERE id = ?", (bill_id,))
        conn.commit()

# ======================
# Debug Helper
# ======================
if __name__ == "__main__":
    print("Accounts:", get_accounts())
    print("Recent Transactions:", get_transactions())
    print("Upcoming Bills:", get_upcoming_bills(14))
