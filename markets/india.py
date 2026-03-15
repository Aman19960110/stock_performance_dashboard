import pandas as pd

class India_Market():

    def __init__(self):
        pass
    def load_csv(self):
        df = pd.read_csv(r"stock_list/stock_list.csv", index_col=0)
        df.fillna(0, inplace=True)
        df.sort_values(by="market_cap", ascending=False, inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    
    def get_symbols(self,df_group):
        return [s + ".NS" for s in df_group["SYMBOL"].tolist()]