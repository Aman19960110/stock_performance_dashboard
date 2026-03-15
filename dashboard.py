import streamlit as st
import pandas as pd
import math
import yfinance as yf
import plotly.graph_objects as go
import utils.helpers_functions as hf

from datetime import date, timedelta
from config import Settings
from markets.us import Us_Market
from markets.india import India_Market

st.set_page_config(page_title="Stock Performance Dashboard", layout="wide")
st.title('Dashboard')

st.sidebar.header("Parameters")

settings = Settings()

start_date, end_date = st.sidebar.date_input(
    "Select Date Range",
    value=(settings.start_date, settings.end_date),
    
)

choice = st.sidebar.selectbox('Select the Market',['US','China','Japan','India','UK','Hong Kong','Germany','France','Canada','Australia'])

market, stock_df, group_size = hf.get_market(choice)

# =========================
# Group Selector
# =========================


total_groups = hf.total_groups(stock_df,group_size)
st.sidebar.subheader("S&P500 Group")

group_no = st.sidebar.selectbox(
    "Select Group",
    options=list(range(1, total_groups + 1))
)


df_group = hf.get_group(group_no,group_size,stock_df)

st.subheader(f"Selected Stock Group (Group {group_no})")
st.dataframe(df_group, use_container_width=True)

# =========================
# Download Price Data
# =========================
symbols = market.get_symbols(df_group)

price_df = hf.get_data(symbols,start_date,end_date)

if price_df.empty:
    st.warning("No price data available.")
    st.stop()

# =========================
# Returns Calculation
# =========================
total_pct_df = hf.calculate_returs(price_df)

# =========================
# Plot Filter
# =========================
st.sidebar.subheader("Plot Filter")

filter_option = st.sidebar.radio(
    "Show stocks",
    [
        "All stocks",
        "Above mean (last value)",
        "Above median (last value)",
        "Above std (last value)",
        "Above 2 std (last value)"
    ]
)



fig = hf.build_chart(total_pct_df, filter_option)
st.plotly_chart(fig, use_container_width=True)
