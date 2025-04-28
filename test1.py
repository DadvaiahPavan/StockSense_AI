import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# List of Yahoo Finance pages to scrape
urls = {
    "Most Active": "https://finance.yahoo.com/markets/stocks/most-active/",
    "Trending Now": "https://finance.yahoo.com/markets/stocks/trending/",
    "Top Gainers": "https://finance.yahoo.com/markets/stocks/gainers/",
    "Top Losers": "https://finance.yahoo.com/markets/stocks/losers/",
    "52 Week Gainers": "https://finance.yahoo.com/markets/stocks/52-week-gainers/",
    "52 Week Losers": "https://finance.yahoo.com/markets/stocks/52-week-losers/"
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def scrape_table(url):
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch {url}")
        return pd.DataFrame()

    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table')
    
    if not table:
        print(f"No table found at {url}")
        return pd.DataFrame()

    headers_list = []
    for th in table.find_all('th'):
        headers_list.append(th.text.strip())

    rows = []
    for tr in table.find('tbody').find_all('tr'):
        row = []
        for td in tr.find_all('td'):
            row.append(td.text.strip())
        rows.append(row)

    df = pd.DataFrame(rows, columns=headers_list)
    return df

# Main
all_data = {}

for name, url in urls.items():
    print(f"Scraping: {name}")
    df = scrape_table(url)
    if not df.empty:
        all_data[name] = df
    time.sleep(2)  # polite scraping delay

# Save to CSV files
for name, df in all_data.items():
    filename = name.lower().replace(' ', '_') + '.csv'
    df.to_csv(filename, index=False)
    print(f"Saved {filename}")

print("Scraping Completed!")
