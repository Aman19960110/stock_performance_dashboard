import streamlit as st
import plotly.express as px
import utils.helpers_functions as hf
from screener_scrapper import ScreenerClient
import os
from pathlib import Path

from config import Settings

st.set_page_config(page_title="Stock Performance Dashboard", layout="wide")
st.title("Stock Performance Dashboard")

st.sidebar.header("Parameters")

settings = Settings()

date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(settings.start_date, settings.end_date),
)

if len(date_range) != 2:
    st.info("Select both a start and end date to load the dashboard.")
    st.stop()

start_date, end_date = date_range
if start_date >= end_date:
    st.error("Start date must be before end date.")
    st.stop()

choice = st.sidebar.selectbox(
    "Select the Market",
    list(hf.MARKET_CONFIG.keys()),
)

market, stock_df, group_size = hf.get_market(choice)

# =========================
# Group Selector
# =========================


total_groups = hf.total_groups(stock_df, group_size)
st.sidebar.subheader("Group")

group_no = st.sidebar.selectbox(
    "Select Group",
    options=list(range(1, total_groups + 1))
)


df_group = hf.get_group(group_no, group_size, stock_df)

# Create label dict for plot
label_column = hf.MARKET_LABEL_COLUMNS.get(choice, "SYMBOL")
if label_column in df_group.columns:
    label_dict = dict(zip(df_group["SYMBOL"], df_group[label_column]))
else:
    label_dict = {s: s for s in df_group["SYMBOL"]}

# =========================
# Download Price Data
# =========================
symbols = tuple(market.get_symbols(df_group))

with st.spinner("Downloading price data..."):
    price_df = hf.get_data(symbols, start_date, end_date)

if price_df.empty:
    st.warning("No price data available.")
    st.stop()

# =========================
# Returns Calculation
# =========================
total_pct_df = hf.calculate_returns(price_df)

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


stock_cols = [c for c in total_pct_df.columns if c not in hf.STATS_COLUMNS]
last_returns = total_pct_df[stock_cols].iloc[-1].sort_values(ascending=False)
best_symbol = last_returns.index[0]
worst_symbol = last_returns.index[-1]
mean_return = total_pct_df["mean_pct_chg"].iloc[-1]

metric_cols = st.columns(4)
metric_cols[0].metric("Stocks Loaded", len(stock_cols),border= True)
metric_cols[1].metric("Mean Return", f"{mean_return:.2f}%",border= True)
metric_cols[2].metric("Best Performer", label_dict.get(best_symbol, best_symbol), f"{last_returns.iloc[0]:.2f}%",border= True)
metric_cols[3].metric("Weakest Performer", label_dict.get(worst_symbol, worst_symbol), f"{last_returns.iloc[-1]:.2f}%",border= True)

fig = hf.build_chart(total_pct_df, filter_option, label_dict)

chart_tab, movers_tab, highs_tab, sectors_tab, stocks_tab = st.tabs(
    ["Returns", "Rank Movers", "52-Week Highs", "Sectors", "Stocks"]
)

with chart_tab:
    st.plotly_chart(fig, use_container_width=True)
    if choice == "India":

        symbols_list = sorted(
            df_group["SYMBOL"]
            .dropna()
            .unique()
            .tolist()
        )

        selected_stock = st.selectbox(
            "Select Stock",
            options=symbols_list,
            index=None,
            placeholder="Choose a stock...",
            
        )
        if selected_stock == None:
            st.stop()

        if selected_stock:

            try:

                top_ratios, quick_ratios = hf.get_screener_ratios(
                    selected_stock
                )

                Mcap = top_ratios.get(
                    "Market Cap",
                    "N/A"
                )

                current_price = top_ratios.get(
                    "Current Price",
                    "N/A"
                )

                High_low = top_ratios.get(
                    "High / Low",
                    "N/A"
                )

                stock_pe = top_ratios.get(
                    "Stock P/E",
                    "N/A"
                )

                change_in_prom_hold = quick_ratios.get(
                    "Change in Prom Hold",
                    "N/A"
                )

                eps = quick_ratios.get(
                    "EPS",
                    "N/A"
                )

                change_in_fii_holding = quick_ratios.get(
                    'Chg in FII Hold',
                    'N/A'
                )

                change_in_dii_holding = quick_ratios.get(
                    'Chg in DII Hold',
                    'N/A'
                )

                public_holding = quick_ratios.get(
                    'Public holding',
                    'N/A'
                )


                st.subheader('Stock Ratios')

                    # First row
                row1 = st.columns(3)

                row1[0].metric(
                    "Market Cap",
                    Mcap,
                    border= True
                )

                row1[1].metric(
                    "Current Price",
                    current_price,
                    border= True
                )

                row1[2].metric(
                    "High / Low",
                    High_low,
                    border= True
                )

                # Second row
                row2 = st.columns(3)

                row2[0].metric(
                    "Stock P/E",
                    stock_pe,
                    border= True
                )

                row2[1].metric(
                    "Change in Prom Hold",
                    change_in_prom_hold,
                    border= True
                )

                row2[2].metric(
                    "EPS",
                    eps,
                    border= True
                )
                row3 = st.columns(3)
                row3[0].metric('Chg in FII hold',change_in_fii_holding,border=True )
                row3[1].metric('Chg in DII hold',change_in_dii_holding,border=True)
                row3[2].metric('Public Holding',public_holding,border=True)


            except Exception as e:

                st.error(
                    f"Failed to fetch Screener data for "
                    f"{selected_stock}"
                )

                st.exception(e)
        st.subheader('Peer comparison')
        peer_df = hf.get_peers_comparision(selected_stock)
        st.dataframe(peer_df)
    
        

with movers_tab:
    st.sidebar.subheader("Rank Delta")
    if len(total_pct_df) < 2:
        st.info("Rank delta needs at least two price rows.")
    else:
        default_n_days = min(10, len(total_pct_df) - 1)
        n_days = st.sidebar.number_input(
            "N-days Ago",
            min_value=1,
            max_value=len(total_pct_df) - 1,
            value=default_n_days,
            step=1,
        )
        rank_delta_df = hf.calculate_pct_rank_delta(total_pct_df, n_days)
        st.dataframe(rank_delta_df, use_container_width=True)

with highs_tab:
    with st.spinner("Scanning stocks making new 52-week highs..."):
        stock_df_above_52w = hf.get_stocks_above_52w_high(market, df_group)
    st.dataframe(stock_df_above_52w, use_container_width=True)

with sectors_tab:
    with st.spinner("Calculating equal weighted sector performance..."):
        sector_perf = hf.get_sector_performance_timeseries(df_group, market)

    if sector_perf.empty:
        st.info("No sector performance data available for this group.")
    else:
        plot_df = sector_perf.reset_index()
        sector_fig = px.line(
            plot_df,
            x="Date",
            y=sector_perf.columns,
            title="Equal Weighted Sector Performance",
        )

        sector_fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Normalized Index (Base = 100)",
            template="plotly_white",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            margin=dict(l=20, r=20, t=80, b=40),
        )

        st.plotly_chart(sector_fig, use_container_width=True)

with stocks_tab:
    st.subheader(f"Selected Stock Group (Group {group_no})")
    st.dataframe(df_group, use_container_width=True)
