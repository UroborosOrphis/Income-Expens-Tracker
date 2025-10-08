# db/seed.py
import sqlite3
from pathlib import Path

DB_PATH = Path("db/expenses.db")

def seed_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # --- Accounts ---
    accounts = [
        ("Cash Wallet", "wallet", 0, 1),
        ("Bank Account", "bank", 0, 1),
        ("Credit Card", "credit_card", 0, 1),
    ]
    cursor.executemany(
        "INSERT INTO accounts (name, type, virtual_balance, active) VALUES (?, ?, ?, ?)",
        accounts,
    )

    # --- Categories ---
    categories = [
        ("Salary", "💰", "income"),
        ("Groceries", "🛒", "expense"),
        ("Transport", "🚌", "expense"),
        ("Dining", "🍽️", "expense"),
        ("Fees", "💳", "expense"),
    ]
    cursor.executemany(
        "INSERT INTO categories (name, emoji, type) VALUES (?, ?, ?)",
        categories,
    )

    # --- Transactions ---
    transactions = [
        # Income
        (2, 1, 3000.00, "income", "2025-10-01", "Monthly Salary", "October salary", 0, None),
        # Expense
        (2, 2, 150.00, "expense", "2025-10-02", "Groceries at Tesco", None, 0, None),
        # Transfer: Bank -> Wallet
        (2, None, -200.00, "transfer", "2025-10-03", "Reload wallet", None, 0, None),
        (1, None, 200.00, "transfer", "2025-10-03", "Reload from bank", None, 0, None),
        # Credit card fee
        (3, 5, 2.00, "expense", "2025-10-03", "Processing fee", None, 0, None),
    ]
    cursor.executemany(
        """INSERT INTO transactions
        (account_id, category_id, amount, type, date, description, notes, is_recurring, receipt_image_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        transactions,
    )

    # --- Transfers (link the reload) ---
    cursor.execute(
        "INSERT INTO transfers (from_transaction_id, to_transaction_id) VALUES (?, ?)",
        (3, 4),  # IDs of the two transfer transactions above
    )

    # --- Bills ---
    bills = [
        ("Internet Bill", 120.00, "2025-10-15", "monthly", 2),
        ("Electricity Bill", 80.00, "2025-10-20", "monthly", 2),
    ]
    cursor.executemany(
        "INSERT INTO bills (name, amount, due_date, repeat_freq, account_id) VALUES (?, ?, ?, ?, ?)",
        bills,
    )

    # --- Subscriptions ---
    subscriptions = [
        ("Netflix", "monthly", "2025-10-10", 3, 4, None, 1),
        ("Spotify", "monthly", "2025-10-12", 3, 4, None, 1),
    ]
    cursor.executemany(
        """INSERT INTO subscriptions
        (name, frequency, next_due_date, account_id, category_id, last_posted_date, active)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        subscriptions,
    )

    conn.close()
    print("Database seeded successfully!")

if __name__ == "__main__":
    seed_db()
