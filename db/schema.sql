-- Accounts: bank, wallet, credit card, etc.
CREATE TABLE accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  type TEXT NOT NULL, -- 'bank', 'wallet', 'credit_card'
  virtual_balance REAL DEFAULT 0,
  active INTEGER DEFAULT 1
);

-- Categories: groceries, transport, salary, etc.
CREATE TABLE categories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  emoji TEXT,
  type TEXT NOT NULL -- 'income' or 'expense'
);

-- Transactions: income, expense, transfer
CREATE TABLE transactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL,
  category_id INTEGER,
  amount REAL NOT NULL,
  type TEXT NOT NULL, -- 'income', 'expense', 'transfer'
  date TEXT NOT NULL,
  description TEXT,
  notes TEXT,
  is_recurring INTEGER DEFAULT 0,
  FOREIGN KEY (account_id) REFERENCES accounts(id),
  FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- Transfers: links two transactions (from and to)
CREATE TABLE transfers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  from_transaction_id INTEGER,
  to_transaction_id INTEGER,
  FOREIGN KEY (from_transaction_id) REFERENCES transactions(id),
  FOREIGN KEY (to_transaction_id) REFERENCES transactions(id)
);

-- Bills: recurring payments like rent, utilities
CREATE TABLE bills (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  amount REAL NOT NULL,
  due_date TEXT NOT NULL,
  repeat_freq TEXT NOT NULL, -- 'monthly', 'weekly', etc.
  account_id INTEGER NOT NULL,
  FOREIGN KEY (account_id) REFERENCES accounts(id)
);

-- Reminder log: tracks when reminders were sent
CREATE TABLE reminder_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bill_id INTEGER NOT NULL,
  sent_date TEXT NOT NULL,
  FOREIGN KEY (bill_id) REFERENCES bills(id)
);

-- Subscriptions: recurring charges with variable amounts
CREATE TABLE subscriptions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  frequency TEXT NOT NULL, -- 'monthly', 'yearly', etc.
  next_due_date TEXT NOT NULL,
  account_id INTEGER NOT NULL,
  category_id INTEGER,
  last_posted_date TEXT,
  active INTEGER DEFAULT 1,
  FOREIGN KEY (account_id) REFERENCES accounts(id),
  FOREIGN KEY (category_id) REFERENCES categories(id)
);

