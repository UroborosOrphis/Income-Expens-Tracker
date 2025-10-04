import sqlite3
import pandas as pd
from pathlib import Path
import sys

# Streamlit and Plotly libraries
import streamlit as st
import plotly.express as px

# ======================
# Configuration & Paths
# ======================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "db" / "expenses.db"


# ======================
# Data Fetching and Preparation
# ======================

@st.cache_data
def fetch_transaction_data():
    """Fetches all transaction data and prepares a DataFrame (cached by Streamlit)."""
    if not DB_PATH.exists():
        st.error(f"Error: Database file not found at {DB_PATH}.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)

    query = """
    SELECT 
        t.date, 
        t.amount, 
        t.category, 
        t.description, 
        a.name AS account_name,
        t.type AS transaction_type
    FROM transactions t
    JOIN accounts a ON t.account_id = a.id
    ORDER BY t.date ASC;
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        return pd.DataFrame()

    # Prepare data columns
    df['signed_amount'] = df.apply(
        lambda row: -row['amount'] if row['transaction_type'] == 'expense' else row['amount'],
        axis=1
    )
    df['date'] = pd.to_datetime(df['date'])

    return df


# ======================
# Streamlit Dashboard Layout
# ======================

def render_dashboard():
    """Renders the dashboard using Streamlit commands."""

    st.set_page_config(layout="wide", page_title="Personal Finance Tracker")
    st.title("💸 Personal Expense & Income Dashboard")

    df = fetch_transaction_data()

    if df.empty:
        st.warning("No transactions found in the database to display.")
        return

    # --- Sidebar Filtering (Optional but useful for single users) ---
    st.sidebar.header("Filter Options")

    # Date Range Filter
    min_date = df['date'].min().to_pydatetime()
    max_date = df['date'].max().to_pydatetime()
    date_range = st.sidebar.date_input(
        "Select Date Range",
        [min_date, max_date]
    )

    # Apply date filter
    if len(date_range) == 2:
        start_date = pd.to_datetime(date_range[0])
        end_date = pd.to_datetime(date_range[1])
        df_filtered = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    else:
        df_filtered = df.copy()

    # --- Summary Cards (KPIs) ---

    total_expense = df_filtered[df_filtered['transaction_type'] == 'expense']['amount'].sum()
    total_income = df_filtered[df_filtered['transaction_type'] == 'income']['amount'].sum()
    net_flow = total_income - total_expense

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Expenses", f"RM {total_expense:,.2f}", delta_color="inverse")
    col2.metric("Total Income", f"RM {total_income:,.2f}")
    col3.metric("Net Flow", f"RM {net_flow:,.2f}", delta=net_flow, delta_color="normal")

    st.markdown("---")

    # --- Main Charts ---

    col_chart_1, col_chart_2 = st.columns(2)

    # 1. Cumulative Balance Over Time (Line Chart)
    with col_chart_1:
        st.subheader("Cumulative Balance")

        # Calculate daily net flow and cumulative sum
        daily_net_flow = df_filtered.groupby('date')['signed_amount'].sum().cumsum().reset_index()

        fig_line = px.line(
            daily_net_flow,
            x='date',
            y='signed_amount',
            labels={'signed_amount': 'Cumulative Flow (RM)', 'date': 'Date'},
            title='Cumulative Net Flow Over Time'
        )
        fig_line.update_layout(hovermode="x unified")
        st.plotly_chart(fig_line, use_container_width=True)

    # 2. Expense Distribution Pie Chart
    with col_chart_2:
        st.subheader("Expense Distribution")

        expense_df = df_filtered[df_filtered['transaction_type'] == 'expense']
        category_summary = expense_df.groupby('category')['amount'].sum().reset_index()

        fig_pie = px.pie(
            category_summary,
            values='amount',
            names='category',
            title='Spending Distribution by Category',
            hole=.5
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    # --- Detailed Transaction Table ---
    st.subheader("Detailed Transaction Log")
    st.dataframe(
        df_filtered[[
            'date', 'amount', 'category', 'account_name', 'description', 'transaction_type'
        ]].rename(columns={
            'account_name': 'Account',
            'transaction_type': 'Type',
            'amount': 'Amount',
            'date': 'Date',
            'category': 'Category',
            'description': 'Description'
        }),
        use_container_width=True
    )


# ======================
# Execution
# ======================

if __name__ == "__main__":
    render_dashboard()