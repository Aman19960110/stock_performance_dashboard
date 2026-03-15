import pandas as pd

class Tsx():

    def __init__(self):
        pass
    def load_csv(self):
        df = pd.read_csv(r"stock_list/TSX.csv")
        df.fillna(0, inplace=True)
        df.rename(columns={'Ticker':'SYMBOL'},inplace=True)
        df.sort_values(by="MarketCap", ascending=False, inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    
    def get_symbols(self,df_group):
        return [s + ".TO" for s in df_group["SYMBOL"].tolist()]