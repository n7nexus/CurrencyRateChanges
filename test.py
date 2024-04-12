import pandas as pd

url = 'http://www.iban.ru/currency-codes'
url2 = 'https://www.finmarket.ru/currency/rates/?id=10148&pv=1&cur=52170&bd=1&bm=2&by=2022&ed=1&em=2&ey=2024&x=48&y=13#archive'

html = pd.read_html(url, thousands=None)

print(html)

html2 = pd.read_html(url2, encoding="windows-1251", decimal=",", thousands=None)

# print(html2)
print(html2[1].head())


