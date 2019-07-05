#Universe generating SP500 DataList

import bs4 as bs
import pickle
import requests

resp = requests.get('https://www.slickcharts.com/sp500')
soup = bs.BeautifulSoup(resp.text, 'lxml')
table = soup.find('table', {'class': 'table table-hover table-borderless table-sm'})
universe = []
for row in table.findAll('tr')[1:]:
    ticker = row.findAll('td')[2].text
    universe.append(ticker)

with open('sp500tickers.pickle', 'wb') as f:
    pickle.dump(universe, f)

print(universe)





