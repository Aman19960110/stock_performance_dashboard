import pandas as pd

class Asx200():

    def __init__(self):
        pass
    def load_csv(self):
        df = pd.read_csv(r"stock_list/ASX200.csv")
        df.fillna(0, inplace=True)
        df.rename(columns={'Code':'SYMBOL','Market Capitalisation':'MarketCap'},inplace=True)
        df.sort_values(by="MarketCap", ascending=False, inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    
    def get_symbols(self,df_group):
        return [s + ".AX" for s in df_group["SYMBOL"].tolist()]