import math
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import os
from pathlib import Path
from screener_scrapper import ScreenerClient
from difflib import get_close_matches

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


def normalize_symbol(symbol):
    if symbol is None or (isinstance(symbol, float) and pd.isna(symbol)):
        return None

    text = str(symbol).strip().upper()
    if not text:
        return None

    text = text.replace(" ", "")
    if "." in text:
        text = text.split(".", 1)[0]

    return text


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


def _vwap_frame(downloaded):
    if downloaded.empty:
        return pd.DataFrame()

    if isinstance(downloaded.columns, pd.MultiIndex):
        if "Close" not in downloaded.columns.get_level_values(0):
            return pd.DataFrame()
        close = downloaded["Close"]
        high = downloaded["High"]
        low = downloaded["Low"]
        volume = downloaded["Volume"]
    else:
        if "Close" not in downloaded.columns:
            return pd.DataFrame()
        close = downloaded["Close"]
        high = downloaded["High"]
        low = downloaded["Low"]
        volume = downloaded["Volume"]

    # Calculate VWAP for each symbol
    vwap_dict = {}
    if isinstance(close, pd.DataFrame):
        for col in close.columns:
            typical_price = (close[col] + high[col] + low[col]) / 3
            vwap = (typical_price * volume[col]).cumsum() / volume[col].cumsum()
            vwap_dict[col] = vwap
    else:
        typical_price = (close + high + low) / 3
        vwap = (typical_price * volume).cumsum() / volume.cumsum()
        vwap_dict[close.name] = vwap

    vwap_df = pd.DataFrame(vwap_dict)
    return vwap_df.dropna(axis=1, how="all")


@st.cache_data(show_spinner=False, ttl=60 * 60)
def get_data(symbols, start, end, price_type="Close"):
    downloaded = yf.download(
        list(symbols),
        start=start,
        end=end,
        progress=False,
        auto_adjust=True,
        group_by="column",
    )
    
    if price_type == "VWAP":
        return _vwap_frame(downloaded)
    else:
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

    hovermode="closest",   # <-- see point 2

    legend=dict(
        orientation="v",   # vertical
        yanchor="top",
        y=1,
        xanchor="left",
        x=1.02,            # place outside plot area
    ),

    margin=dict(
        l=20,
        r=100,             # extra space for legend
        t=80,
        b=40
    ),
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


@st.cache_data(show_spinner=False, ttl=60 * 60)
def build_sector_performance_chart(df_group, _market):
    """Build a cached sector performance chart with equal weighted indices."""
    sector_perf = get_sector_performance_timeseries(df_group, _market)
    
    if sector_perf.empty:
        return None
    
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
        hovermode="closest",
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
        margin=dict(l=20, r=20, t=80, b=40),
    )

    return sector_fig


def build_peer_comparison_chart(peer_df, stock_df, total_pct_df, label_dict=None):
    """Build a chart for peer comparison based on peer_df company names using fuzzy matching."""
    if peer_df.empty:
        st.error("Peer comparison dataframe is empty")
        return None
    
    peer_symbols = []
    
    # Try to get symbols from peer_df directly
    if 'SYMBOL' in peer_df.columns:
        peer_symbols = peer_df['SYMBOL'].dropna().tolist()
    elif 'Symbol' in peer_df.columns:
        peer_symbols = peer_df['Symbol'].dropna().tolist()
    elif 'Name' in peer_df.columns:
        # Create a mapping from company names to symbols using fuzzy matching
        label_col = "NAME OF COMPANY"
        
        if label_col in stock_df.columns:
            # Get list of company names from stock_df
            company_names = stock_df[label_col].dropna().tolist()
            name_to_symbol = dict(zip(company_names, stock_df[stock_df[label_col].notna()]['SYMBOL'].tolist()))
            
            # For each peer name, find the most similar company name
            peer_names = peer_df['Name'].dropna().tolist()
            for peer_name in peer_names:
                peer_name_clean = str(peer_name).strip()
                
                # Find close matches (cutoff=0.6 means 60% similarity)
                matches = get_close_matches(peer_name_clean, company_names, n=1, cutoff=0.6)
                
                if matches:
                    matched_name = matches[0]
                    symbol = name_to_symbol.get(matched_name)
                    if symbol:
                        peer_symbols.append(symbol)
    
    if not peer_symbols:
        st.error(f"Could not match peer names to symbols. Peer columns: {peer_df.columns.tolist()}")
        return None

    normalized_peer_symbols = [normalize_symbol(symbol) for symbol in peer_symbols if normalize_symbol(symbol)]
    if not normalized_peer_symbols:
        st.error(f"Could not normalize peer symbols. Peers: {peer_symbols}")
        return None
    
    # Filter returns data for peers only
    stock_cols = [c for c in total_pct_df.columns if c not in STATS_COLUMNS]
    normalized_stock_cols = {normalize_symbol(col): col for col in stock_cols if normalize_symbol(col)}
    peer_cols = []
    for peer_symbol in normalized_peer_symbols:
        matched_col = normalized_stock_cols.get(peer_symbol)
        if matched_col:
            peer_cols.append(matched_col)
    
    if not peer_cols:
        st.error(f"No peer symbols found in returns data. Peers: {normalized_peer_symbols}, Available: {stock_cols}")
        return None
    
    # Create filtered dataframe
    peer_pct_df = total_pct_df[peer_cols].copy()
    
    # Calculate stats for peer group
    peer_pct_df["mean_pct_chg"] = peer_pct_df.mean(axis=1)
    peer_pct_df["median_pct_change"] = peer_pct_df.median(axis=1)
    peer_pct_df["std"] = peer_pct_df.drop(columns=["mean_pct_chg", "median_pct_change"]).std(axis=1)
    peer_pct_df["2std"] = 2 * peer_pct_df["std"]
    
    # Build chart using existing build_chart function
    fig = build_chart(peer_pct_df, "All stocks", label_dict)
    
    if fig:
        fig.update_layout(title="Peer Comparison - Returns Performance")
    
    return fig




@st.cache_resource
def get_screener_client():

    # Load .env only once
    for line in Path(".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if (
            line
            and not line.startswith("#")
            and "=" in line
        ):
            key, value = line.split("=", 1)
            os.environ.setdefault(
                key.strip(),
                value.strip()
            )

    return ScreenerClient(
        username=os.environ["SCREENER_USERNAME"],
        password=os.environ["SCREENER_PASSWORD"],
    )


@st.cache_data(ttl=3600)
def get_screener_ratios(symbol):

    client = get_screener_client()

    top_ratios = client.get_top_ratios(symbol)
    quick_ratios = client.get_quick_ratios(symbol, "other")

    return top_ratios, quick_ratios

@st.cache_data(ttl=3600)
def get_peers_comparision(symbol):

    client = get_screener_client()
    
    peers_df = client.get_peer_comparison(symbol)
    return peers_df

@st.cache_data(ttl=3600)
def get_fund_manger_stock(fund_manger):

    client = get_screener_client()
    
    mask = client.full_text_search(fund_manger)
    return mask