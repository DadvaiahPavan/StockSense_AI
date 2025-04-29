"""
Yahoo Finance scraper using BeautifulSoup for reliable data extraction
"""
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime

def get_yahoo_market_stocks(category='most-active'):
    """
    Get stock data from Yahoo Finance for different categories
    
    Args:
        category: Category of stocks to fetch. Options:
            - 'most-active'
            - 'trending'
            - 'gainers'
            - 'losers'
            - '52-week-gainers'
            - '52-week-losers'
    
    Returns:
        List of dictionaries with stock data
    """
    # Map categories to Yahoo Finance URLs
    category_urls = {
        'most-active': "https://finance.yahoo.com/markets/stocks/most-active/",
        'trending': "https://finance.yahoo.com/markets/stocks/trending/",
        'gainers': "https://finance.yahoo.com/markets/stocks/gainers/",
        'losers': "https://finance.yahoo.com/markets/stocks/losers/",
        '52-week-gainers': "https://finance.yahoo.com/markets/stocks/52-week-high/",
        '52-week-losers': "https://finance.yahoo.com/markets/stocks/52-week-low/"
    }
    
    if category not in category_urls:
        return {'error': f'Invalid category: {category}'}
    
    url = category_urls[category]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    print(f"Scraping: {category} from {url}")
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch {url}")
            return {'error': f'Failed to fetch data: HTTP {response.status_code}'}

        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table')
        
        if not table:
            print(f"No table found at {url}")
            return {'error': 'No table found on page'}

        # Extract table headers
        headers_list = []
        for th in table.find_all('th'):
            headers_list.append(th.text.strip())
        
        print(f"Found headers: {headers_list}")
        
        # Extract rows
        rows_data = []
        for tr in table.find('tbody').find_all('tr'):
            row = []
            for td in tr.find_all('td'):
                row.append(td.text.strip())
            rows_data.append(row)

        # Convert to pandas DataFrame for easier processing
        df = pd.DataFrame(rows_data, columns=headers_list)
        print(f"DataFrame shape: {df.shape}")
        
        # Find the index of key columns based on headers
        column_mapping = {
            'Symbol': 'symbol',
            'Name': 'name',
            'Price': 'price',
            'Change': 'change',
            'Change %': 'change_percent',
            'Volume': 'volume',
            'Avg Vol (3M)': 'avg_volume',
            'Market Cap': 'market_cap',
            'P/E Ratio (TTM)': 'pe_ratio'
        }
        
        # Convert DataFrame to list of dictionaries for dashboard
        stocks_data = []
        
        # Process each row in the DataFrame
        for _, row in df.iterrows():
            try:
                stock = {}
                # Stock Symbol
                stock['symbol'] = row.iloc[0]
                
                # Stock Name
                stock['name'] = row.iloc[1]
                
                # Price
                try:
                    price_raw = row.iloc[3] if len(row) > 3 else "0.0"
                    # Extract numeric value from price text (handle currency symbols and commas)
                    if isinstance(price_raw, str):
                        # Remove currency symbols, commas and extra text
                        price_clean = price_raw.replace('$', '').replace(',', '').strip()
                        # If there's any space, take just the first part (the actual price)
                        if ' ' in price_clean:
                            price_clean = price_clean.split()[0]
                        # If there's anything that's not a digit, period, plus or minus, replace it
                        price_clean = ''.join(c for c in price_clean if c.isdigit() or c == '.' or c == '+' or c == '-')
                        if price_clean:
                            stock['price'] = float(price_clean)
                        else:
                            # Get directly from HTML if parsing fails
                            print(f"Price parsing failed for {stock['symbol']} with value '{price_raw}'. Using raw value.")
                            stock['price'] = float(price_raw) if isinstance(price_raw, (int, float)) else 0.0
                    else:
                        stock['price'] = float(price_raw) if price_raw else 0.0
                    
                    # Debug output
                    print(f"Price for {stock['symbol']}: raw='{price_raw}', cleaned={stock['price']}")
                except (ValueError, TypeError) as e:
                    print(f"Price conversion error for {stock['symbol']}: {e}")
                    stock['price'] = 0.0
                
                # Change
                try:
                    change_raw = row.iloc[4] if len(row) > 4 else "0.0"
                    # Handle +/- signs
                    if isinstance(change_raw, str):
                        stock['change'] = float(change_raw.replace(',', ''))
                    else:
                        stock['change'] = float(change_raw) if change_raw else 0.0
                except (ValueError, TypeError):
                    stock['change'] = 0.0
                
                # Change Percent
                try:
                    change_pct_raw = row.iloc[5] if len(row) > 5 else "0.0%"
                    # Remove % sign and convert to float
                    if isinstance(change_pct_raw, str):
                        change_pct_clean = change_pct_raw.replace('%', '').replace(',', '')
                        stock['change_percent'] = float(change_pct_clean)
                    else:
                        stock['change_percent'] = float(change_pct_raw) if change_pct_raw else 0.0
                except (ValueError, TypeError):
                    stock['change_percent'] = 0.0
                
                # Volume
                try:
                    volume_raw = row.iloc[6] if len(row) > 6 else "0"
                    # Handle K, M, B suffixes
                    if isinstance(volume_raw, str):
                        multiplier = 1
                        if 'K' in volume_raw:
                            multiplier = 1000
                            volume_raw = volume_raw.replace('K', '')
                        elif 'M' in volume_raw:
                            multiplier = 1000000
                            volume_raw = volume_raw.replace('M', '')
                        elif 'B' in volume_raw:
                            multiplier = 1000000000
                            volume_raw = volume_raw.replace('B', '')
                        
                        volume_clean = volume_raw.replace(',', '')
                        stock['volume'] = float(volume_clean) * multiplier if volume_clean else 0
                    else:
                        stock['volume'] = float(volume_raw) if volume_raw else 0
                except (ValueError, TypeError):
                    stock['volume'] = 0
                
                # Average Volume
                try:
                    avg_vol_raw = row.iloc[7] if len(row) > 7 else "0"
                    # Handle K, M, B suffixes
                    if isinstance(avg_vol_raw, str):
                        multiplier = 1
                        if 'K' in avg_vol_raw:
                            multiplier = 1000
                            avg_vol_raw = avg_vol_raw.replace('K', '')
                        elif 'M' in avg_vol_raw:
                            multiplier = 1000000
                            avg_vol_raw = avg_vol_raw.replace('M', '')
                        elif 'B' in avg_vol_raw:
                            multiplier = 1000000000
                            avg_vol_raw = avg_vol_raw.replace('B', '')
                        
                        avg_vol_clean = avg_vol_raw.replace(',', '')
                        stock['avg_volume'] = float(avg_vol_clean) * multiplier if avg_vol_clean else 0
                    else:
                        stock['avg_volume'] = float(avg_vol_raw) if avg_vol_raw else 0
                except (ValueError, TypeError):
                    stock['avg_volume'] = 0
                
                # Market Cap
                stock['market_cap'] = row.iloc[8] if len(row) > 8 else "N/A"
                
                # P/E Ratio
                try:
                    pe_raw = row.iloc[9] if len(row) > 9 else "N/A"
                    if pe_raw != "N/A" and pe_raw:
                        stock['pe_ratio'] = float(str(pe_raw).replace(',', ''))
                    else:
                        stock['pe_ratio'] = "N/A"
                except (ValueError, TypeError):
                    stock['pe_ratio'] = "N/A"
                
                # 52 Week Change %
                try:
                    week52_change_raw = row.iloc[10] if len(row) > 10 else "N/A"
                    if isinstance(week52_change_raw, str) and week52_change_raw.strip() != "N/A":
                        # Remove percentage signs, parentheses, and commas
                        week52_clean = week52_change_raw.replace('%', '').replace(',', '').replace('(', '').replace(')', '').strip()
                        # Handle the '+' sign
                        if '+' in week52_clean:
                            week52_clean = week52_clean.replace('+', '')
                        # Handle negative values with parentheses
                        if week52_clean.startswith('-'):
                            stock['week52_change'] = -float(week52_clean.replace('-', '')) if week52_clean.replace('-', '') else 0.0
                        else:
                            stock['week52_change'] = float(week52_clean) if week52_clean else 0.0
                    else:
                        stock['week52_change'] = "N/A"
                except (ValueError, TypeError):
                    stock['week52_change'] = "N/A"
                
                print(f"Processed stock: {stock['symbol']} - Price: {stock['price']}")
                stocks_data.append(stock)
            except Exception as e:
                print(f"Error processing stock: {e}")
        
        print(f"Successfully processed {len(stocks_data)} stocks for {category}")
        return stocks_data
        
    except Exception as e:
        import traceback
        print(f"Error scraping {category}: {e}")
        traceback.print_exc()
        return {'error': str(e)}

# For testing
if __name__ == "__main__":
    categories = [
        'most-active',
        'trending',
        'gainers',
        'losers',
        '52-week-gainers',
        '52-week-losers'
    ]
    
    for category in categories:
        print(f"\nFetching {category}...")
        data = get_yahoo_market_stocks(category)
        if isinstance(data, list):
            print(f"Found {len(data)} stocks")
            if data:
                print("Sample data:", data[0])
        else:
            print("Error:", data.get('error', 'Unknown error'))
