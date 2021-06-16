import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup

def getAugmentTables(url):
    html = requests.get(url).content
    df_list = pd.read_html(html)
    
    merged = {}
    for df in df_list:
        if 'Name' in df and 'Effects' in df:
            subset_df = df.set_index('Name')
            #subset_df['Weapon Sources'] = subset_df['Weapon Sources'].apply(lambda x: str(x).replace('\n',','))
            #subset_df['Weapon Sources'] = subset_df['Weapon Sources'].apply(lambda x: str(x).replace('\br',','))
            dict = subset_df.to_dict(orient='index')
            
            merged = {**merged, **dict}
            #print(subset_df)
    keys = merged.keys()
    
    print(merged['Might V']['Weapon Sources'])
     
def main():
    getAugmentTables('https://pso2na.arks-visiphone.com/wiki/Augment_Factors')
    """
    for i in SAFLinks:
        print(i)
    """
main()