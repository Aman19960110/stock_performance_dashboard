import pandas as pd

class China():

    def __init__(self):
        pass
    def load_csv(self):
        df = pd.read_csv(r"stock_list/china_csi_300.csv", index_col=0)
        df.rename(columns={'Ticker': 'SYMBOL'},inplace=True)
        df.fillna(0, inplace=True)
        df.sort_values(by="Weighting (%)", ascending=False, inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    
    def get_symbols(self,df_group):
        return df_group["SYMBOL"].tolist()