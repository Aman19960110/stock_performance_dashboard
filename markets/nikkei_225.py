import pandas as pd

class Nikkei():

    def __init__(self):
        pass
    def load_csv(self):
        df = pd.read_csv(r"stock_list/nikkei_225.csv", index_col=0)
        df.fillna(0, inplace=True)
        df.rename(columns={'Symbol': 'SYMBOL'},inplace=True)
        df.sort_values(by="Market cap", ascending=False, inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    
    def get_symbols(self,df_group):
        return [str(s) + ".T" for s in df_group["SYMBOL"].tolist()]