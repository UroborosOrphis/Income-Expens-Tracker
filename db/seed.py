import sqlite3
from pathlib import Path

DB_PATH = Path("db/expenses.db")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Insert sample accounts
cursor.execute("INSERT INTO accounts (name, type, balance) VALUES (?, ?, ?)",
               ("Cash Wallet", "cash", 500))
cursor.execute("INSERT INTO accounts (name, type, balance) VALUES (?, ?, ?)",
               ("Maybank Credit Card", "credit_card", 0))

# Insert sample bill
cursor.execute("""INSERT INTO bills (account_id, name, amount, due_date, pay_from, pay_until) 
                  VALUES (?, ?, ?, ?, ?, ?)""",
               (2, "Maybank CC September", 1200, "2025-10-20", "2025-10-05", "2025-10-20"))

conn.commit()
conn.close()

print("Sample data inserted ✅")
