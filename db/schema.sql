-- ================================
-- Expense Tracker Database Schema
-- ================================

-- Table for expense/income categories
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    emoji TEXT,
    type TEXT CHECK(type IN ('income','expense')) DEFAULT 'expense'
);

-- Table for different accounts (bank, wallet, credit card, etc.)
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    type TEXT CHECK(type IN ('cash','bank','credit_card','wallet')) NOT NULL,
    balance REAL DEFAULT 0
);

-- Table for income and expense transactions
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    date TEXT NOT NULL, -- ISO format: YYYY-MM-DD
    amount REAL NOT NULL,
    category TEXT,
    description TEXT,
    type TEXT CHECK(type IN ('income','expense','transfer')) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts (id)
);

-- Table for recurring bills / credit card due dates
CREATE TABLE IF NOT EXISTS bills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER,
    name TEXT NOT NULL,
    amount REAL,
    due_date TEXT NOT NULL,
    pay_from TEXT,
    pay_until TEXT,
    is_paid INTEGER DEFAULT 0,
    FOREIGN KEY (account_id) REFERENCES accounts (id)
);

-- Table to track reminders already sent (prevents spam)
CREATE TABLE IF NOT EXISTS reminders_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id INTEGER,
    reminder_date TEXT NOT NULL,
    message TEXT,
    FOREIGN KEY (bill_id) REFERENCES bills (id)
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category);
CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id);