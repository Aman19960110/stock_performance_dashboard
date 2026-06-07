import math
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import streamlit as st

from markets.us import Us_Market
from markets.india import India_Market
from markets.china_csi_300 import China
import markets.nikkei_225
from markets.ftse_100 import Ftse
from markets.germany import Dax
from markets.france import Cac
from markets.canada import Tsx
from markets.asx200 import Asx200


STATS_COLUMNS = ["mean_pct_chg", "median_pct_change", "std", "2std"]

MARKET_LABEL_COLUMNS = {
    "US": "SECURITY",
    "India": "NAME OF COMPANY",
    "China": "Company",
    "Japan": "Company",
    "UK": "Company",
    "Germany": "Company",
    "France": "Company",
    "Canada": "Company",
    "Australia": "Company",
}

MARKET_CONFIG = {
    "US": (Us_Market, 50),
    "India": (India_Market, 200),
    "China": (China, 50),
    "Japan": (markets.nikkei_225.Nikkei, 50),
    "UK": (Ftse, 20),
    "Germany": (Dax, 10),
    "France": (Cac, 10),
    "Canada": (Tsx, 25),
    "Australia": (Asx200, 25),
}


def get_group(group_no, group_size, df):
    start_idx = (group_no - 1) * group_size
    end_idx = start_idx + group_size
    df_group = df.iloc[start_idx:end_idx]

    return df_group

def total_groups(df, group_size):
    total_groups = math.ceil(len(df) / group_size)
    return total_groups

def _close_frame(downloaded):
    if downloaded.empty:
        return pd.DataFrame()

    if isinstance(downloaded.columns, pd.MultiIndex):
        if "Close" not in downloaded.columns.get_level_values(0):
            return pd.DataFrame()
        close = downloaded["Close"]
    else:
        if "Close" not in downloaded.columns:
            return pd.DataFrame()
        close = downloaded["Close"]

    if isinstance(close, pd.Series):
        close = close.to_frame()

    return close.dropna(axis=1, how="all")


@st.cache_data(show_spinner=False, ttl=60 * 60)
def get_data(symbols, start, end):
    downloaded = yf.download(
        list(symbols),
        start=start,
        end=end,
        progress=False,
        auto_adjust=True,
        group_by="column",
    )
    return _close_frame(downloaded)

def calculate_returns(price_df):
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

    return total_pct_df

def calculate_returs(price_df):
    return calculate_returns(price_df)

def cross_up(stock, level):
    return (stock.shift(1) < level.shift(1)) & (stock >= level)

def get_market(choice):
    market_class, default_group_size = MARKET_CONFIG[choice]
    market = market_class()
    stock_df = market.load_csv()
    max_group_size = min(300, len(stock_df))
    group_size = st.sidebar.number_input(
        "Select the length of group",
        min_value=1,
        max_value=max_group_size,
        value=min(default_group_size, max_group_size),
        step=1,
    )
    return market, stock_df, group_size


def build_chart(total_pct_df, filter_option, label_dict=None):
    if label_dict is None:
        label_dict = {col: col for col in total_pct_df.columns}
    stock_cols = [c for c in total_pct_df.columns if c not in STATS_COLUMNS]

    last_vals = total_pct_df.iloc[-1]

    # =========================
    # Cross Detection
    # =========================


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
                    name=label_dict.get(col, col),
                    opacity=0.8,
                    line=dict(width=2)
                )
            )

        elif crossed_before:

            fig.add_trace(
                go.Scatter(
                    x=total_pct_df.index,
                    y=total_pct_df[col],
                    name=f"{label_dict.get(col, col)} (hist)",
                    opacity=0.6,
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
        line=dict(dash="dot", width=3, color="#1f2937")
    ))

    fig.add_trace(go.Scatter(
        x=total_pct_df.index,
        y=total_pct_df["median_pct_change"],
        name="Median",
        line=dict(dash="dot", width=3, color="#2563eb")
    ))

    fig.add_trace(go.Scatter(
        x=total_pct_df.index,
        y=total_pct_df["std"],
        name="Std Dev",
        line=dict(dash="dot", width=3, color="#dc2626")
    ))

    fig.add_trace(go.Scatter(
        x=total_pct_df.index,
        y=total_pct_df["2std"],
        name="2 Std Dev",
        line=dict(dash="dot", width=3, color="#7c3aed")
    ))

    # =========================
    # Layout
    # =========================
    fig.update_layout(
        title=f"Stocks ({filter_option})",
        xaxis_title="Date",
        yaxis_title="Cumulative % Return",
        template="plotly_white",
        height=650,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=20, r=20, t=80, b=40),
    )
    return fig


def calculate_pct_rank_delta(df, n_days):
    stock_cols = df.columns.drop(STATS_COLUMNS, errors="ignore")

    if df.empty or n_days <= 0 or n_days >= len(df):
        return pd.DataFrame(columns=["current_day_rank", "n_days_ago_rank", "rank_delta"])

    pct_rank = df[stock_cols].rank(axis=1, pct=True) * 100
    n_days_ago = pct_rank.iloc[-1 - n_days].round().astype(int)
    current_day = pct_rank.iloc[-1].round().astype(int)
    current_day.rename("current_day_rank", inplace=True)
    n_days_ago.rename("n_days_ago_rank", inplace=True)
    delta_df = pd.merge(current_day, n_days_ago, left_index=True, right_index=True, how="inner")
    delta_df["rank_delta"] = delta_df["current_day_rank"] - delta_df["n_days_ago_rank"]
    delta_df.sort_values(by="rank_delta", ascending=False, inplace=True)
    
    return delta_df




@st.cache_data(show_spinner=False, ttl=60 * 60)
def _get_stocks_above_52w_high(symbols):
    downloaded = yf.download(
        list(symbols),
        period="1y",
        auto_adjust=False,
        progress=False,
        group_by="column",
    )

    if downloaded.empty:
        return pd.DataFrame(columns=["stock", "previous_52w_high", "current_close"])

    if isinstance(downloaded.columns, pd.MultiIndex):
        if "High" not in downloaded.columns.get_level_values(0) or "Close" not in downloaded.columns.get_level_values(0):
            return pd.DataFrame(columns=["stock", "previous_52w_high", "current_close"])
        highs = downloaded["High"]
        closes = downloaded["Close"]
    else:
        if "High" not in downloaded.columns or "Close" not in downloaded.columns:
            return pd.DataFrame(columns=["stock", "previous_52w_high", "current_close"])
        highs = downloaded["High"].to_frame(name=symbols[0])
        closes = downloaded["Close"].to_frame(name=symbols[0])

    data = []
    for stock in symbols:
        if stock not in highs.columns or stock not in closes.columns:
            continue

        high = highs[stock].dropna()
        close = closes[stock].dropna()
        if len(high) < 2 or close.empty:
            continue

        previous_52w_high = high.iloc[:-1].max()
        current_close = close.iloc[-1]
        if pd.isna(previous_52w_high) or pd.isna(current_close):
            continue

        data.append({
            "stock": stock,
            "previous_52w_high": previous_52w_high,
            "current_close": current_close
        })

    df_result = pd.DataFrame(data)
    if df_result.empty:
        return df_result

    return df_result[df_result["current_close"] >= df_result["previous_52w_high"]].reset_index(drop=True)


def get_stocks_above_52w_high(market, df_group):
    symbols = tuple(market.get_symbols(df_group))
    return _get_stocks_above_52w_high(symbols)



def get_sector_performance_timeseries(df_group,market, period="1y"):

    sector_perf = pd.DataFrame()
    if "Sector" not in df_group.columns:
        return sector_perf

    for sector, group in df_group.groupby("Sector"):

        tickers = market.get_symbols(group)
        try:
            prices = yf.download(
                tickers,
                period=period,
                auto_adjust=True,
                progress=False
            )["Close"]

            # Single ticker sector
            if isinstance(prices, pd.Series):
                prices = prices.to_frame()

            prices = prices.dropna(axis=1, how="all")
            if prices.empty:
                continue

            # Normalize to 100
            normalized = prices.div(prices.iloc[0]).mul(100)

            # Equal weighted sector index
            sector_index = normalized.mean(axis=1)

            sector_perf[sector] = sector_index

        except Exception as e:
            print(f"{sector}: {e}")

    return sector_perf
