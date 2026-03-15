import math
import yfinance as yf
import plotly.graph_objects as go
import utils.helpers_functions as hf
import streamlit as st

from markets.us import Us_Market
from markets.india import India_Market
from markets.china_csi_300 import China
import markets.nikkei_225
from markets.ftse_100 import Ftse
from markets.germany import Dax
from markets.france import Cac
from markets.canada import Tsx


def get_group(group_no,group_size,df):
    start_idx = (group_no - 1) * group_size
    end_idx = start_idx + group_size
    df_group = df.iloc[start_idx:end_idx]

    return df_group

def total_groups(df,group_size):
    total_groups = math.ceil(len(df) / group_size)
    return total_groups

def get_data(symbols,start,end):
    df = yf.download(symbols,start,end,progress=False)['Close']
    return df

def calculate_returs(price_df):
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

def cross_up(stock, level):
    return (stock.shift(1) < level.shift(1)) & (stock >= level)

def get_market(choice):
    if choice == 'US':

        market = Us_Market()
        stock_df = market.load_csv()
        group_size =  st.sidebar.number_input('Select the length of group',0,300,50)
    elif choice == 'India':
        market = India_Market()
        stock_df = market.load_csv()
        group_size =  st.sidebar.number_input('Select the length of group',0,300,200)
    elif choice == 'China':
        market = China()
        stock_df = market.load_csv()
        group_size =  st.sidebar.number_input('Select the length of group',0,300,50)
    elif choice == 'Japan':
        market = markets.nikkei_225.Nikkei()
        stock_df = market.load_csv()
        group_size =  st.sidebar.number_input('Select the length of group',0,300,50)
    elif choice == 'UK':
        market = Ftse()
        stock_df = market.load_csv()
        group_size =  st.sidebar.number_input('Select the length of group',0,300,20)
    elif choice == 'Germany':
        market = Dax()
        stock_df = market.load_csv()
        group_size = st.sidebar.number_input('Select the length of group',0,300,10)
    elif choice == 'France':
        market = Cac()
        stock_df = market.load_csv()
        group_size = st.sidebar.number_input('Select the length of group',0,300,10)
    elif choice == 'Canada':
        market = Tsx()
        stock_df = market.load_csv()
        group_size = st.sidebar.number_input('Select the length of group',0,300,25)
    return market,stock_df,group_size


def build_chart(total_pct_df,filter_option):
    stats_cols = ["mean_pct_chg","median_pct_change","std","2std"]
    stock_cols = [c for c in total_pct_df.columns if c not in stats_cols]

    last_vals = total_pct_df.iloc[-1]

    # =========================
    # Cross Detection
    # =========================


    cross_mean = total_pct_df[stock_cols].apply(
        lambda s: hf.cross_up(s,total_pct_df["mean_pct_chg"])
    )

    cross_median = total_pct_df[stock_cols].apply(
        lambda s: hf.cross_up(s,total_pct_df["median_pct_change"])
    )

    cross_1sd = total_pct_df[stock_cols].apply(
        lambda s: hf.cross_up(s,total_pct_df["std"])
    )

    cross_2sd = total_pct_df[stock_cols].apply(
        lambda s: hf.cross_up(s,total_pct_df["2std"])
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
        title=f"Stocks ({filter_option})",
        xaxis_title="Date",
        yaxis_title="Cumulative % Return",
        template="plotly_white",
        height=650
    )
    return fig