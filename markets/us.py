import pandas as pd

class Us_Market():

    def __init__(self):
        pass
    def load_csv(self):
        df = pd.read_csv(r'stock_list/snp_list.csv',index_col = 0)
        df = df.rename(columns={
            'Symbol':'SYMBOL',
            'Security': 'SECURITY'
        })
        df = df.sort_values(by='MarketCap',ascending=False)
        df.reset_index(drop=True,inplace=True)

        return df
    
    def get_symbols(self,df_group):
        return df_group["SYMBOL"].tolist()