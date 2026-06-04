import streamlit as st
import pandas as pd
import math
import yfinance as yf
import numpy as np
import plotly.graph_objects as go
import utils.helpers_functions as hf

from datetime import date, timedelta
from config import Settings
from markets.us import Us_Market
from markets.india import India_Market



st.set_page_config(page_title="52 Week High", layout="wide")
st.title('Dashboard')

st.sidebar.header("Parameters")

choice = st.sidebar.selectbox('Select the Market',['US','China','Japan','India','UK','Germany','France','Canada','Australia'])

market, stock_df, group_size = hf.get_market(choice)

total_groups = hf.total_groups(stock_df,group_size)
st.sidebar.subheader("Group")

group_no = st.sidebar.selectbox(
    "Select Group",
    options=list(range(1, total_groups + 1))
)

df_group = hf.get_group(group_no,group_size,stock_df)

stock_df_above_52w = hf.get_stocks_above_52w_high(market,df_group)
st.dataframe(stock_df_above_52w)