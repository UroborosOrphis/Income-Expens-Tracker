# Income Expense Tracker

Personal Project to create my own self-hosted Income Expense Tracker

## Features
- **Desktop automation (`pc_bot/`)**: Scripts for importing bank statements, syncing data, and generating reports.
- **Discord cloud bot (`cloud_bot/`)**: Collect expenses via slash commands and buffer them for later database sync.
- **SQLite backend (`db/`)**: Central schema and initialization scripts for persisting accounts, categories, transactions, bills, and subscriptions.
- **Transfer utilities (`Transfers/`)**: Some tools to help statement conversion

## Repository Structure
```text
.
├── cloud_bot/           # Discord bot and shared configuration JSON files
├── db/                  # Database schema, seed data, and management scripts
├── pc_bot/              # Local automation scripts (database manager, reports, processors)
├── Transfers/           # Statement conversion utilities
├── requirements.txt     # Python dependencies
└── README.md            # You are here
```





