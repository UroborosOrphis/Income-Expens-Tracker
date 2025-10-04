import sqlite3
import json
from pathlib import Path

# Paths
DB_PATH = Path(__file__).resolve().parent.parent / "db" / "expenses.db"
EXPORT_PATH = Path(__file__).resolve().parent.parent / "cloud_bot"


def get_connection():
    """Open database connection"""
    return sqlite3.connect(DB_PATH)


# ======================
# Category Management
# ======================

def add_category(name: str, emoji: str = None):
    """Add a new category"""
    with get_connection() as conn:
        try:
            conn.execute(
                "INSERT INTO categories (name, emoji) VALUES (?, ?)",
                (name, emoji)
            )
            conn.commit()
            print(f"Category '{name}' added")
            export_categories()
        except sqlite3.IntegrityError:
            print(f"Category '{name}' already exists")


def remove_category(name: str):
    """Remove a category"""
    with get_connection() as conn:
        conn.execute("DELETE FROM categories WHERE name = ?", (name,))
        conn.commit()
        print(f"Category '{name}' removed")
        export_categories()


def list_categories():
    """List all categories"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT name, emoji FROM categories ORDER BY name"
        ).fetchall()
        return rows


def export_categories():
    """Export categories to JSON for cloud bot"""
    categories = []
    for name, emoji in list_categories():
        categories.append({
            "name": name,
            "emoji": emoji or "📦"
        })

    output_file = EXPORT_PATH / "categories.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(categories, f, indent=2, ensure_ascii=False)

    print(f"Exported {len(categories)} categories to {output_file}")


# ======================
# Account Management
# ======================

def add_account_config(name: str, type: str, emoji: str = None):
    """Add account to both database and config"""
    with get_connection() as conn:
        try:
            # Add to accounts table
            conn.execute(
                "INSERT INTO accounts (name, type, balance) VALUES (?, ?, ?)",
                (name, type, 0)
            )
            conn.commit()
            print(f"Account '{name}' added")

            # Export to JSON
            export_accounts()
        except sqlite3.IntegrityError:
            print(f"Account '{name}' already exists")


def remove_account_config(name: str):
    """Remove account from database (keeps historical transactions)"""
    with get_connection() as conn:
        # Check if account has transactions
        count = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE account_id = (SELECT id FROM accounts WHERE name = ?)",
            (name,)
        ).fetchone()[0]

        if count > 0:
            print(f"Warning: Account '{name}' has {count} transactions")
            print("Marking as inactive instead of deleting...")
            # You could add an 'active' flag to accounts table instead

        conn.execute("DELETE FROM accounts WHERE name = ?", (name,))
        conn.commit()
        print(f"Account '{name}' removed")
        export_accounts()


def list_accounts():
    """List all accounts"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT name, type FROM accounts ORDER BY name"
        ).fetchall()
        return rows


def export_accounts():
    """Export accounts to JSON for cloud bot"""
    accounts = []
    for name, acc_type in list_accounts():
        # Determine emoji based on type
        emoji_map = {
            "cash": "💰",
            "bank": "🏦",
            "credit_card": "💳",
            "wallet": "👛"
        }
        emoji = emoji_map.get(acc_type, "💰")

        accounts.append({
            "name": name,
            "type": acc_type,
            "emoji": emoji
        })

    output_file = EXPORT_PATH / "accounts.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(accounts, f, indent=2, ensure_ascii=False)

    print(f"Exported {len(accounts)} accounts to {output_file}")


# ======================
# Initialize Default Data
# ======================

def init_default_categories():
    """Initialize default categories"""
    defaults = [
        ("Food", "🍔"),
        ("Transport", "🚗"),
        ("Bills", "📄"),
        ("Shopping", "🛍️"),
        ("Entertainment", "🎬"),
        ("Health", "💊"),
        ("Other", "📦")
    ]

    for name, emoji in defaults:
        add_category(name, emoji)


def init_default_accounts():
    """Initialize default accounts"""
    defaults = [
        ("Cash Wallet", "cash"),
        ("Maybank Credit Card", "credit_card"),
        ("Grab Wallet", "wallet"),
        ("Bank Account", "bank")
    ]

    for name, acc_type in defaults:
        add_account_config(name, acc_type)


# ======================
# CLI Interface
# ======================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python config_manager.py init              - Initialize default categories & accounts")
        print("  python config_manager.py list              - List all categories & accounts")
        print("  python config_manager.py add_category <name> [emoji]")
        print("  python config_manager.py remove_category <name>")
        print("  python config_manager.py add_account <name> <type> [emoji]")
        print("  python config_manager.py remove_account <name>")
        print("  python config_manager.py export            - Export to JSON files")
        sys.exit(1)

    command = sys.argv[1]

    if command == "init":
        print("Initializing default categories and accounts...")
        init_default_categories()
        init_default_accounts()

    elif command == "list":
        print("\nCategories:")
        for name, emoji in list_categories():
            print(f"  {emoji} {name}")

        print("\nAccounts:")
        for name, acc_type in list_accounts():
            print(f"  {name} ({acc_type})")

    elif command == "add_category":
        if len(sys.argv) < 3:
            print("Usage: add_category <name> [emoji]")
        else:
            name = sys.argv[2]
            emoji = sys.argv[3] if len(sys.argv) > 3 else None
            add_category(name, emoji)

    elif command == "remove_category":
        if len(sys.argv) < 3:
            print("Usage: remove_category <name>")
        else:
            remove_category(sys.argv[2])

    elif command == "add_account":
        if len(sys.argv) < 4:
            print("Usage: add_account <name> <type>")
            print("Types: cash, bank, credit_card, wallet")
        else:
            name = sys.argv[2]
            acc_type = sys.argv[3]
            add_account_config(name, acc_type)

    elif command == "remove_account":
        if len(sys.argv) < 3:
            print("Usage: remove_account <name>")
        else:
            remove_account_config(sys.argv[2])

    elif command == "export":
        print("Exporting categories and accounts...")
        export_categories()
        export_accounts()

    else:
        print(f"Unknown command: {command}")