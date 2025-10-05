# pc_bot/statement_processor.py

import sqlite3
import pandas as pd
from pathlib import Path
from io import StringIO
import sys

# Streamlit is used for the interactive review interface
import streamlit as st

# ======================
# Configuration & Setup
# ======================
# Paths adjusted for execution from pc_bot/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "db" / "expenses.db"

# --- REQUIRED CSV COLUMNS ---
REQUIRED_COLUMNS = ['Date', 'Amount', 'Description']


# ----------------------------


# ======================
# DB and Configuration Helpers
# ======================

@st.cache_data(ttl=3600)
def load_db_config():
    """Loads all accounts and categories for validation and dropdowns."""
    if not DB_PATH.exists():
        st.error(f"Database file not found at: {DB_PATH.resolve()}")
        st.stop()

    conn = sqlite3.connect(DB_PATH)
    accounts_df = pd.read_sql_query("SELECT id, name FROM accounts", conn)
    categories_df = pd.read_sql_query("SELECT name FROM categories", conn)
    conn.close()

    return accounts_df, categories_df


def insert_approved_transaction(data: dict):
    """Inserts a single approved transaction into the transactions table."""
    conn = sqlite3.connect(DB_PATH)

    account_id_result = conn.execute("SELECT id FROM accounts WHERE name = ?", (data['account_name'],)).fetchone()
    if not account_id_result:
        conn.close()
        raise ValueError(f"Account '{data['account_name']}' not found in DB.")

    account_id = account_id_result[0]

    sql = """
          INSERT INTO transactions (account_id, date, amount, category, description, type)
          VALUES (?, ?, ?, ?, ?, ?) \
          """

    try:
        amount_val = abs(data['amount'])

        conn.execute(sql, (
            account_id,
            data['date'],
            amount_val,
            data['category'],
            data['description'],
            data['type']
        ))
        conn.commit()
        st.toast(f"✅ Logged: {data['type'].upper()} of {amount_val:,.2f} ({data['category']})", icon="💰")
    except sqlite3.Error as e:
        st.error(f"DB Error on insertion: {e}")
        conn.rollback()
    finally:
        conn.close()


# ======================
# Data Parsing Function
# ======================

def parse_csv_data(uploaded_content_mock) -> list:
    """Reads CSV-like data into a DataFrame and formats it for review."""
    if uploaded_content_mock is None:
        return []

    try:
        stringio = StringIO(uploaded_content_mock.getvalue().decode("utf-8"))
        df = pd.read_csv(stringio, sep=None, engine='python')
    except Exception as e:
        st.error(f"Failed to read data as CSV: {e}")
        return []

    if not all(col in df.columns for col in REQUIRED_COLUMNS):
        missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        st.error(
            f"Parsed data is missing required columns: {', '.join(missing)}. "
            f"Columns found: {list(df.columns)}. "
        )
        return []

    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
    df = df.dropna(subset=['Amount']).reset_index(drop=True)

    review_list = []
    for index, row in df.iterrows():
        amount = row['Amount']

        review_list.append({
            "date": pd.to_datetime(row['Date'], errors='coerce').strftime('%Y-%m-%d'),
            "amount": amount,
            "type": 'expense' if amount < 0 else 'income',
            "account_name": "Need Review",
            "category": "Need Review",
            "description": str(row['Description']).strip()
        })

    return review_list


# ======================
# Streamlit Review App
# ======================

def statement_processor_app():
    """Main Streamlit app for statement review."""
    st.set_page_config(page_title="Statement Processor", layout="wide")
    st.title("📄 CSV Statement Processor & Review")
    st.markdown("---")

    accounts_df, categories_df = load_db_config()
    accounts_list = accounts_df['name'].tolist()
    categories_list = categories_df['name'].tolist()

    if 'transactions_to_review' not in st.session_state:
        st.session_state.transactions_to_review = []

    # --- INPUT SECTION (File Upload & Parsing) ---
    if not st.session_state.transactions_to_review:
        with st.expander("Upload or Paste CSV Statement Data", expanded=True):
            st.info(
                f"Upload a CSV file or paste CSV-formatted text. "
                f"Headers required: **{', '.join(REQUIRED_COLUMNS)}**"
            )

            uploaded_file = st.file_uploader("Upload CSV File", type=['csv'])

            raw_statement = st.text_area(
                "Paste CSV-formatted data here",
                height=200
            )

            if st.button("🔬 Parse Data", use_container_width=True, disabled=not (uploaded_file or raw_statement)):

                content_to_parse = None

                if uploaded_file:
                    content_to_parse = uploaded_file
                elif raw_statement:
                    class MockUploadedFile:
                        def getvalue(self):
                            return raw_statement.encode("utf-8")

                    content_to_parse = MockUploadedFile()

                if content_to_parse:
                    with st.spinner('Parsing text/CSV lines...'):
                        parsed_list = parse_csv_data(content_to_parse)

                        st.session_state.transactions_to_review = parsed_list
                        st.success(f"Loaded {len(parsed_list)} transactions for review.")
                        st.rerun()

    # --- REVIEW SECTION ---
    if st.session_state.transactions_to_review:
        st.header("Review and Approve Transactions")
        st.info(f"Found {len(st.session_state.transactions_to_review)} transactions pending review.")

        default_accounts = ["Need Review"] + accounts_list
        default_categories = ["Need Review"] + categories_list

        review_list = st.session_state.transactions_to_review[::-1]

        for i, tx in enumerate(review_list):
            original_index = len(st.session_state.transactions_to_review) - 1 - i

            with st.container(border=True):
                display_amount = abs(tx['amount'])
                st.subheader(f"Transaction #{original_index + 1}: **{tx['type'].upper()}** of ${display_amount:,.2f}")

                col_date, col_amount, col_type = st.columns([1.5, 1, 1])

                tx['date'] = col_date.date_input(
                    "Date",
                    value=pd.to_datetime(tx.get('date', pd.Timestamp.today().date())),
                    key=f"date_{original_index}"
                ).strftime('%Y-%m-%d')

                tx['amount'] = col_amount.number_input(
                    "Amount (Negative for Expense)",
                    value=float(tx.get('amount', 0.0)),
                    key=f"amount_{original_index}"
                )

                tx['type'] = col_type.selectbox(
                    "Type",
                    options=['expense', 'income'],
                    index=['expense', 'income'].index(tx.get('type', 'expense').lower()),
                    key=f"type_{original_index}"
                )

                col_account, col_category = st.columns(2)

                tx['account_name'] = col_account.selectbox(
                    "Account",
                    options=default_accounts,
                    index=default_accounts.index("Need Review"),
                    key=f"account_{original_index}"
                )

                tx['category'] = col_category.selectbox(
                    "Category",
                    options=default_categories,
                    index=default_categories.index("Need Review"),
                    key=f"category_{original_index}"
                )

                tx['description'] = st.text_input(
                    "Description",
                    value=tx.get('description', ''),
                    key=f"desc_{original_index}"
                )

                col_approve, col_delete, _ = st.columns(3)

                can_approve = tx['account_name'] != "Need Review" and tx['category'] != "Need Review"

                if col_approve.button("✅ Approve & Insert", key=f"approve_{original_index}", use_container_width=True,
                                      disabled=not can_approve, type="primary"):
                    try:
                        data_to_insert = st.session_state.transactions_to_review[original_index]
                        insert_approved_transaction(data_to_insert)

                        del st.session_state.transactions_to_review[original_index]
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to insert: {e}")

                if col_delete.button("🗑️ Delete", key=f"delete_{original_index}", use_container_width=True):
                    del st.session_state.transactions_to_review[original_index]
                    st.rerun()


if __name__ == "__main__":
    statement_processor_app()