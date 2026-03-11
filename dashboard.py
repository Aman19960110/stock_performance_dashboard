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
st.title("Stock Performance Dashboard")

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

choice = st.sidebar.selectbox('Select the Market',['NSE','S&P500'])

if choice == 'NSE':
    # =========================
    # Load Stock List
    # =========================
    stock_mcap_df = pd.read_csv("stock_list.csv", index_col=0)
    stock_mcap_df.fillna(0, inplace=True)
    stock_mcap_df.sort_values(by="market_cap", ascending=False, inplace=True)
    stock_mcap_df.reset_index(drop=True, inplace=True)

    # =========================
    # NIFTY 50 Symbols
    # =========================
    nifty_50_symbols = [
    "ADANIENT","ADANIPORTS","APOLLOHOSP","ASIANPAINT","AXISBANK","BAJAJAUTO",
    "BAJFINANCE","BAJAJFINSV","BEL","BHARTIARTL","CIPLA","COALINDIA","DRREDDY",
    "EICHERMOT","ETERNAL","GRASIM","HCLTECH","HDFCBANK","HDFCLIFE","HINDALCO",
    "HINDUNILVR","ICICIBANK","ITC","INFY","INDIGO","JSWSTEEL","JIOFIN",
    "KOTAKBANK","LT","M&M","MARUTI","MAXHEALTH","NTPC","NESTLEIND","ONGC",
    "POWERGRID","RELIANCE","SBILIFE","SHRIRAMFIN","SBIN","SUNPHARMA","TCS",
    "TATACONSUM","TMPV","TATASTEEL","TECHM","TITAN","TRENT","ULTRACEMCO","WIPRO"
    ]

    # =========================
    # Group Selector
    # =========================
    group_size = 200
    total_groups = math.ceil(len(stock_mcap_df) / group_size)

    st.sidebar.subheader("Market Cap Group")

    group_options = ["NIFTY_50"] + list(range(1, total_groups + 1))

    group_no = st.sidebar.selectbox(
        "Select Group",
        options=group_options
    )

    if group_no == "NIFTY_50":
        df_group = stock_mcap_df[
            stock_mcap_df["SYMBOL"].isin(nifty_50_symbols)
        ]
    else:
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
        st.warning("No price data available.")
        st.stop()

    # =========================
    # Returns Calculation
    # =========================
    pct_df = price_df.pct_change().fillna(0)
    total_pct_df = ((1 + pct_df).cumprod() - 1) * 100

    total_pct_df["mean_pct_chg"] = total_pct_df.mean(axis=1)
    total_pct_df["median_pct_change"] = total_pct_df.drop(
        columns=["mean_pct_chg"]
    ).median(axis=1)

    total_pct_df["std"] = total_pct_df.drop(
        columns=["mean_pct_chg","median_pct_change"]
    ).std(axis=1)

    total_pct_df["2std"] = 2 * total_pct_df["std"]

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
    # Historical Line Opacity
    # =========================
    st.sidebar.subheader("Historical Line Opacity")

    hist_opacity = st.sidebar.slider(
        "Opacity for historical lines",
        min_value=0.05,
        max_value=0.6,
        value=0.6,
        step=0.05
    )

    # =========================
    # Prepare Data
    # =========================
    stats_cols = ["mean_pct_chg","median_pct_change","std","2std"]
    stock_cols = [c for c in total_pct_df.columns if c not in stats_cols]

    last_vals = total_pct_df.iloc[-1]

    # =========================
    # Cross Detection
    # =========================
    def cross_up(stock, level):
        return (stock.shift(1) < level.shift(1)) & (stock >= level)

    cross_mean = total_pct_df[stock_cols].apply(
        lambda s: cross_up(s,total_pct_df["mean_pct_chg"])
    )

    cross_median = total_pct_df[stock_cols].apply(
        lambda s: cross_up(s,total_pct_df["median_pct_change"])
    )

    cross_1sd = total_pct_df[stock_cols].apply(
        lambda s: cross_up(s,total_pct_df["std"])
    )

    cross_2sd = total_pct_df[stock_cols].apply(
        lambda s: cross_up(s,total_pct_df["2std"])
    )

    # =========================
    # Select Cross Type
    # =========================
    if filter_option == "Above mean (last value)":
        cross_hist = cross_mean
        threshold_col = "mean_pct_chg"

    elif filter_option == "Above median (last value)":
        cross_hist = cross_median
        threshold_col = "median_pct_change"

    elif filter_option == "Above std (last value)":
        cross_hist = cross_1sd
        threshold_col = "std"

    elif filter_option == "Above 2 std (last value)":
        cross_hist = cross_2sd
        threshold_col = "2std"

    else:
        cross_hist = None
        threshold_col = None

    # =========================
    # Plot Chart
    # =========================
    fig = go.Figure()

    for col in stock_cols:

        current_above = False
        crossed_before = False

        if filter_option == "All stocks":
            current_above = True
        else:
            current_above = last_vals[col] > last_vals[threshold_col]
            crossed_before = cross_hist[col].any()

        if current_above:

            fig.add_trace(
                go.Scatter(
                    x=total_pct_df.index,
                    y=total_pct_df[col],
                    name=col,
                    opacity=0.8,
                    line=dict(width=2)
                )
            )

        elif crossed_before:

            fig.add_trace(
                go.Scatter(
                    x=total_pct_df.index,
                    y=total_pct_df[col],
                    name=f"{col} (hist)",
                    opacity=hist_opacity,
                    line=dict(
                        dash="dashdot",
                        width=1
                    )
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

    # =========================
    # Last Day Change Table
    # =========================
    col1, col2 = st.columns(2)

    mask_df = total_pct_df.drop(columns=stats_cols)

    sd_last_row = mask_df.iloc[-2]
    last_row = mask_df.iloc[-1]

    last_day_change = (last_row - sd_last_row).sort_values(ascending=False)

    with col1:
        st.subheader("Last Day Change")
        st.dataframe(last_day_change)

    # =========================
    # Crossing Signals Today
    # =========================
    cross_any = cross_mean | cross_median | cross_1sd | cross_2sd

    today_cross = cross_any.loc[total_pct_df.index[-1]]

    signals = pd.DataFrame(index=total_pct_df.index, columns=stock_cols)

    signals[cross_mean] = "mean"
    signals[cross_median] = "median"
    signals[cross_1sd] = "1sd"
    signals[cross_2sd] = "2sd"

    signals_today = signals.loc[total_pct_df.index[-1]].dropna()

    with col2:
        st.subheader("Signals Today")
        st.dataframe(signals_today)

elif choice == 'S&P500':

    # =========================
    # Load Stock List
    # =========================
    sp500_df = pd.read_csv("snp_list.csv", index_col=0)
    sp500_df = sp500_df.rename(columns={"Symbol":"SYMBOL","Security":"SECURITY",})
    sp500_df = sp500_df.sort_values(by='MarketCap',ascending=False)
    sp500_df.reset_index(drop=True, inplace=True)

    # =========================
    # Group Selector
    # =========================
    group_size = 100
    total_groups = math.ceil(len(sp500_df) / group_size)

    st.sidebar.subheader("S&P500 Group")

    group_no = st.sidebar.selectbox(
        "Select Group",
        options=list(range(1, total_groups + 1))
    )

    start_idx = (group_no - 1) * group_size
    end_idx = start_idx + group_size
    df_group = sp500_df.iloc[start_idx:end_idx]

    st.subheader(f"Selected Stock Group (Group {group_no})")
    st.dataframe(df_group, use_container_width=True)

    # =========================
    # Download Price Data
    # =========================
    symbols = df_group["SYMBOL"].tolist()

    price_df = yf.download(
        symbols,
        start=start_date,
        end=end_date,
        progress=False
    )["Close"]

    if price_df.empty:
        st.warning("No price data available.")
        st.stop()

    # =========================
    # Returns Calculation
    # =========================
    pct_df = price_df.pct_change().fillna(0)
    total_pct_df = ((1 + pct_df).cumprod() - 1) * 100

    total_pct_df["mean_pct_chg"] = total_pct_df.mean(axis=1)
    total_pct_df["median_pct_change"] = total_pct_df.drop(
        columns=["mean_pct_chg"]
    ).median(axis=1)

    total_pct_df["std"] = total_pct_df.drop(
        columns=["mean_pct_chg","median_pct_change"]
    ).std(axis=1)

    total_pct_df["2std"] = 2 * total_pct_df["std"]

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
    # Historical Line Opacity
    # =========================
    st.sidebar.subheader("Historical Line Opacity")

    hist_opacity = st.sidebar.slider(
        "Opacity for historical lines",
        min_value=0.05,
        max_value=0.6,
        value=0.6,
        step=0.05
    )

    # =========================
    # Prepare Data
    # =========================
    stats_cols = ["mean_pct_chg","median_pct_change","std","2std"]
    stock_cols = [c for c in total_pct_df.columns if c not in stats_cols]

    last_vals = total_pct_df.iloc[-1]

    # =========================
    # Cross Detection
    # =========================
    def cross_up(stock, level):
        return (stock.shift(1) < level.shift(1)) & (stock >= level)

    cross_mean = total_pct_df[stock_cols].apply(
        lambda s: cross_up(s,total_pct_df["mean_pct_chg"])
    )

    cross_median = total_pct_df[stock_cols].apply(
        lambda s: cross_up(s,total_pct_df["median_pct_change"])
    )

    cross_1sd = total_pct_df[stock_cols].apply(
        lambda s: cross_up(s,total_pct_df["std"])
    )

    cross_2sd = total_pct_df[stock_cols].apply(
        lambda s: cross_up(s,total_pct_df["2std"])
    )

    # =========================
    # Select Cross Type
    # =========================
    if filter_option == "Above mean (last value)":
        cross_hist = cross_mean
        threshold_col = "mean_pct_chg"

    elif filter_option == "Above median (last value)":
        cross_hist = cross_median
        threshold_col = "median_pct_change"

    elif filter_option == "Above std (last value)":
        cross_hist = cross_1sd
        threshold_col = "std"

    elif filter_option == "Above 2 std (last value)":
        cross_hist = cross_2sd
        threshold_col = "2std"

    else:
        cross_hist = None
        threshold_col = None

    # =========================
    # Plot Chart
    # =========================
    fig = go.Figure()

    for col in stock_cols:

        current_above = False
        crossed_before = False

        if filter_option == "All stocks":
            current_above = True
        else:
            current_above = last_vals[col] > last_vals[threshold_col]
            crossed_before = cross_hist[col].any()

        if current_above:

            fig.add_trace(
                go.Scatter(
                    x=total_pct_df.index,
                    y=total_pct_df[col],
                    name=col,
                    opacity=0.8,
                    line=dict(width=2)
                )
            )

        elif crossed_before:

            fig.add_trace(
                go.Scatter(
                    x=total_pct_df.index,
                    y=total_pct_df[col],
                    name=f"{col} (hist)",
                    opacity=hist_opacity,
                    line=dict(
                        dash="dashdot",
                        width=1
                    )
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
        title=f"S&P500 Performance ({filter_option})",
        xaxis_title="Date",
        yaxis_title="Cumulative % Return",
        template="plotly_white",
        height=650
    )

    st.plotly_chart(fig, use_container_width=True)