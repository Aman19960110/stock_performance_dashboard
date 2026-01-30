from datetime import date, timedelta
import pandas as pd
import streamlit as st
import math
import yfinance as yf
import plotly.graph_objects as go

# =========================
# App Config
# =========================
st.set_page_config(page_title="Stock Performance Dashboard", layout="wide")
st.title("📈 Stock Performance Dashboard")

# =========================
# Sidebar Controls
# =========================
st.sidebar.header("Parameters")

end_date = date.today()
start_date = end_date - timedelta(days=365)

start_date, end_date = st.sidebar.date_input(
    "Select Date Range",
    value=(start_date, end_date),
    max_value=date.today()
)

# =========================
# Load & Prepare Stock List
# =========================
stock_mcap_df = pd.read_csv("stock_list.csv", index_col=0)
stock_mcap_df.fillna(0, inplace=True)
stock_mcap_df.sort_values(by="market_cap", ascending=False, inplace=True)
stock_mcap_df.reset_index(drop=True, inplace=True)

# =========================
# Group Selector (200 stocks)
# =========================
group_size = 200
total_groups = math.ceil(len(stock_mcap_df) / group_size)

st.sidebar.subheader("Market Cap Group")

group_no = st.sidebar.selectbox(
    "Select Group",
    options=range(1, total_groups + 1)
)

start_idx = (group_no - 1) * group_size
end_idx = start_idx + group_size

df_group = stock_mcap_df.iloc[start_idx:end_idx]

st.subheader(f"Selected Stock Group (Group {group_no})")
st.dataframe(df_group, use_container_width=True)

# =========================
# Download Price Data
# =========================
symbols = [s + ".NS" for s in df_group["SYMBOL"].tolist()]

price_df = yf.download(
    symbols,
    start=start_date,
    end=end_date,
    progress=False
)["Close"]

if price_df.empty:
    st.warning("No price data available for selected date range.")
    st.stop()

# =========================
# Returns & Statistics
# =========================
pct_df = price_df.pct_change().fillna(0)
total_pct_df = ((1 + pct_df).cumprod() - 1) * 100

total_pct_df["mean_pct_chg"] = total_pct_df.mean(axis=1)
total_pct_df["median_pct_change"] = total_pct_df.drop(
    columns=["mean_pct_chg"]
).median(axis=1)

total_pct_df["std"] = total_pct_df.drop(
    columns=["mean_pct_chg", "median_pct_change"]
).std(axis=1)

total_pct_df["2std"] = 2 * total_pct_df["std"]

# Optional table display
if st.checkbox("Show performance table (last 50 rows)"):
    st.dataframe(total_pct_df.tail(50), use_container_width=True)

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

# =========================
# Plotly Chart
# =========================
stats_cols = ["mean_pct_chg", "median_pct_change", "std", "2std"]
stock_cols = [c for c in total_pct_df.columns if c not in stats_cols]

last_vals = total_pct_df.iloc[-1]

fig = go.Figure()

# Stock lines (filtered)
for col in stock_cols:
    show = True

    if filter_option == "Above mean (last value)":
        show = last_vals[col] > last_vals["mean_pct_chg"]
    elif filter_option == "Above median (last value)":
        show = last_vals[col] > last_vals["median_pct_change"]
    elif filter_option == "Above std (last value)":
        show = last_vals[col] > last_vals["std"]
    elif filter_option == "Above 2 std (last value)":
        show = last_vals[col] > last_vals["2std"]

    if show:
        fig.add_trace(
            go.Scatter(
                x=total_pct_df.index,
                y=total_pct_df[col],
                name=col,
                opacity=0.6
            )
        )

# =========================
# Reference Lines
# =========================
fig.add_trace(go.Scatter(
    x=total_pct_df.index,
    y=total_pct_df["mean_pct_chg"],
    name="Mean",
    line=dict(dash="dot", width=3, color="black")
))

fig.add_trace(go.Scatter(
    x=total_pct_df.index,
    y=total_pct_df["median_pct_change"],
    name="Median",
    line=dict(dash="dot", width=3, color="blue")
))

fig.add_trace(go.Scatter(
    x=total_pct_df.index,
    y=total_pct_df["std"],
    name="Std Dev",
    line=dict(dash="dot", width=3, color="red")
))

fig.add_trace(go.Scatter(
    x=total_pct_df.index,
    y=total_pct_df["2std"],
    name="2 Std Dev",
    line=dict(dash="dot", width=3, color="purple")
))

# =========================
# Layout
# =========================
fig.update_layout(
    title=f"Stock Performance ({filter_option})",
    xaxis_title="Date",
    yaxis_title="Cumulative % Return",
    template="plotly_white",
    height=650
)

st.plotly_chart(fig, use_container_width=True)
