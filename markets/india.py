import pandas as pd

class India_Market():

    def __init__(self):
        self.yf_ext = '.NS'
    def load_csv(self):
        df = pd.read_csv(r"stock_list/stock_list.csv", index_col=0)
        num_cols = df.select_dtypes(include=["number"]).columns
        str_cols = df.select_dtypes(include=["string", "object"]).columns

        df[num_cols] = df[num_cols].fillna(0)
        df[str_cols] = df[str_cols].fillna("")
        df.fillna(0, inplace=True)
        df.sort_values(by="market_cap", ascending=False, inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    
    def get_symbols(self,df_group):
        return [s + ".NS" for s in df_group["SYMBOL"].tolist()]