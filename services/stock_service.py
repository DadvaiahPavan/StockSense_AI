import yfinance as yf
import pandas as pd
import json
import numpy as np
from datetime import datetime, timedelta
import concurrent.futures

def get_stock_data(symbol, period='1y', interval='1d'):
    """
    Fetch historical stock data using yfinance
    
    Args:
        symbol: Stock ticker symbol
        period: Time period to fetch data for (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
    
    Returns:
        Dictionary with historical data formatted for charts
    """
    try:
        # Get historical data from yfinance
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)
        
        if hist.empty:
            return {'error': f'No data available for {symbol}. Please check the symbol and try again.'}
        
        # Ensure we have required columns
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in hist.columns for col in required_columns):
            return {'error': f'Incomplete data for {symbol}. Missing required price data.'}
        
        # Clean the data - fill NaN values with previous values
        hist = hist.fillna(method='ffill')
        
        # Format data for charts
        dates = hist.index.strftime('%Y-%m-%d').tolist()
        prices = hist['Close'].fillna(method='ffill').tolist()
        volumes = hist['Volume'].fillna(0).astype(int).tolist()
        
        # Calculate moving averages only if we have enough data points
        sma_20 = []
        sma_50 = []
        sma_200 = []
        
        if len(hist) >= 20:
            hist['SMA_20'] = hist['Close'].rolling(window=20, min_periods=1).mean()
            sma_20 = hist['SMA_20'].tolist()
        
        if len(hist) >= 50:
            hist['SMA_50'] = hist['Close'].rolling(window=50, min_periods=1).mean()
            sma_50 = hist['SMA_50'].tolist()
        
        if len(hist) >= 200:
            hist['SMA_200'] = hist['Close'].rolling(window=200, min_periods=1).mean()
            sma_200 = hist['SMA_200'].tolist()
        
        # Calculate OHLC data for candlestick charts
        ohlc = []
        for i, row in hist.iterrows():
            ohlc.append({
                'date': i.strftime('%Y-%m-%d'),
                'open': row['Open'],
                'high': row['High'],
                'low': row['Low'],
                'close': row['Close'],
                'volume': row['Volume']
            })
        
        # Calculate daily returns
        hist['Daily_Return'] = hist['Close'].pct_change() * 100
        daily_returns = hist['Daily_Return'].fillna(0).tolist()
        
        return {
            'dates': dates,
            'prices': prices,
            'volumes': volumes,
            'sma_20': sma_20,
            'sma_50': sma_50,
            'sma_200': sma_200,
            'ohlc': ohlc,
            'daily_returns': daily_returns
        }
    
    except Exception as e:
        print(f"Error fetching stock data for {symbol}: {e}")
        return {'error': f'Error fetching data for {symbol}: {str(e)}'}

def get_stock_info(symbol):
    """
    Get detailed information about a stock
    
    Args:
        symbol: Stock ticker symbol
    
    Returns:
        Dictionary with stock information
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Get real-time price
        hist = ticker.history(period='1d')
        current_price = hist['Close'].iloc[-1] if not hist.empty else None
        
        # Format the data
        stock_info = {
            'symbol': symbol,
            'name': info.get('shortName', info.get('longName', symbol)),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'market_cap': info.get('marketCap', 'N/A'),
            'pe_ratio': info.get('trailingPE', 'N/A'),
            'eps': info.get('trailingEps', 'N/A'),
            'dividend_yield': info.get('dividendYield', 'N/A'),
            'price': current_price,
            'day_high': info.get('dayHigh', 'N/A'),
            'day_low': info.get('dayLow', 'N/A'),
            'fifty_two_week_high': info.get('fiftyTwoWeekHigh', 'N/A'),
            'fifty_two_week_low': info.get('fiftyTwoWeekLow', 'N/A'),
            'volume': info.get('volume', 'N/A'),
            'avg_volume': info.get('averageVolume', 'N/A'),
            'beta': info.get('beta', 'N/A'),
            'description': info.get('longBusinessSummary', 'No description available')
        }
        
        # Calculate additional metrics if data is available
        if current_price and info.get('bookValue'):
            stock_info['price_to_book'] = round(current_price / info['bookValue'], 2)
        
        return stock_info
    
    except Exception as e:
        print(f"Error fetching stock info for {symbol}: {e}")
        return {'error': str(e), 'symbol': symbol, 'name': symbol}

def search_stocks(query):
    """
    Search for stocks by name or symbol with autocomplete functionality
    
    Args:
        query: Search query string
    
    Returns:
        List of matching stocks with symbol and name
    """
    try:
        # Popular US stocks with more comprehensive list
        us_stocks = [
            {'symbol': 'AAPL', 'name': 'Apple Inc.'},
            {'symbol': 'MSFT', 'name': 'Microsoft Corporation'},
            {'symbol': 'GOOGL', 'name': 'Alphabet Inc. (Google)'},
            {'symbol': 'GOOG', 'name': 'Alphabet Inc. Class C'},
            {'symbol': 'AMZN', 'name': 'Amazon.com, Inc.'},
            {'symbol': 'META', 'name': 'Meta Platforms, Inc. (Facebook)'},
            {'symbol': 'TSLA', 'name': 'Tesla, Inc.'},
            {'symbol': 'NVDA', 'name': 'NVIDIA Corporation'},
            {'symbol': 'JPM', 'name': 'JPMorgan Chase & Co.'},
            {'symbol': 'V', 'name': 'Visa Inc.'},
            {'symbol': 'JNJ', 'name': 'Johnson & Johnson'},
            {'symbol': 'UNH', 'name': 'UnitedHealth Group Inc.'},
            {'symbol': 'WMT', 'name': 'Walmart Inc.'},
            {'symbol': 'PG', 'name': 'Procter & Gamble Co.'},
            {'symbol': 'MA', 'name': 'Mastercard Inc.'},
            {'symbol': 'HD', 'name': 'Home Depot Inc.'},
            {'symbol': 'BAC', 'name': 'Bank of America Corp.'},
            {'symbol': 'XOM', 'name': 'Exxon Mobil Corporation'},
            {'symbol': 'AVGO', 'name': 'Broadcom Inc.'},
            {'symbol': 'COST', 'name': 'Costco Wholesale Corporation'},
            {'symbol': 'CSCO', 'name': 'Cisco Systems, Inc.'},
            {'symbol': 'ADBE', 'name': 'Adobe Inc.'},
            {'symbol': 'NFLX', 'name': 'Netflix, Inc.'},
            {'symbol': 'DIS', 'name': 'The Walt Disney Company'},
            {'symbol': 'PEP', 'name': 'PepsiCo, Inc.'},
            {'symbol': 'INTC', 'name': 'Intel Corporation'},
            {'symbol': 'AMD', 'name': 'Advanced Micro Devices, Inc.'},
            {'symbol': 'QCOM', 'name': 'Qualcomm Incorporated'},
            {'symbol': 'PYPL', 'name': 'PayPal Holdings, Inc.'},
            {'symbol': 'SBUX', 'name': 'Starbucks Corporation'}
        ]
        
        # Popular Indian stocks with more comprehensive list and accurate symbols
        indian_stocks = [
            {'symbol': 'RELIANCE.NS', 'name': 'Reliance Industries Limited'},
            {'symbol': 'TCS.NS', 'name': 'Tata Consultancy Services Limited'},
            {'symbol': 'HDFCBANK.NS', 'name': 'HDFC Bank Limited'},
            {'symbol': 'INFY.NS', 'name': 'Infosys Limited'},
            {'symbol': 'HINDUNILVR.NS', 'name': 'Hindustan Unilever Limited'},
            {'symbol': 'ICICIBANK.NS', 'name': 'ICICI Bank Limited'},
            {'symbol': 'SBIN.NS', 'name': 'State Bank of India'},
            {'symbol': 'BHARTIARTL.NS', 'name': 'Bharti Airtel Limited'},
            {'symbol': 'KOTAKBANK.NS', 'name': 'Kotak Mahindra Bank Limited'},
            {'symbol': 'ITC.NS', 'name': 'ITC Limited'},
            {'symbol': 'TATAMOTORS.NS', 'name': 'Tata Motors Limited'},
            {'symbol': 'BAJFINANCE.NS', 'name': 'Bajaj Finance Limited'},
            {'symbol': 'AXISBANK.NS', 'name': 'Axis Bank Limited'},
            {'symbol': 'MARUTI.NS', 'name': 'Maruti Suzuki India Limited'},
            {'symbol': 'HCLTECH.NS', 'name': 'HCL Technologies Limited'},
            {'symbol': 'WIPRO.NS', 'name': 'Wipro Limited'},
            {'symbol': 'SUNPHARMA.NS', 'name': 'Sun Pharmaceutical Industries Limited'},
            {'symbol': 'ASIANPAINT.NS', 'name': 'Asian Paints Limited'},
            {'symbol': 'ONGC.NS', 'name': 'Oil and Natural Gas Corporation Limited'},
            {'symbol': 'TITAN.NS', 'name': 'Titan Company Limited'},
            {'symbol': 'BAJAJFINSV.NS', 'name': 'Bajaj Finserv Limited'},
            {'symbol': 'ADANIENT.NS', 'name': 'Adani Enterprises Limited'},
            {'symbol': 'TATASTEEL.NS', 'name': 'Tata Steel Limited'},
            {'symbol': 'NTPC.NS', 'name': 'NTPC Limited'},
            {'symbol': 'POWERGRID.NS', 'name': 'Power Grid Corporation of India Limited'},
            {'symbol': 'TVSMOTOR.NS', 'name': 'TVS Motor Company Limited'},
            {'symbol': 'TECHM.NS', 'name': 'Tech Mahindra Limited'},
            {'symbol': 'ULTRACEMCO.NS', 'name': 'UltraTech Cement Limited'},
            {'symbol': 'NESTLEIND.NS', 'name': 'Nestle India Limited'},
            {'symbol': 'DRREDDY.NS', 'name': 'Dr. Reddy\'s Laboratories Limited'}
        ]
        
        all_stocks = us_stocks + indian_stocks
        
        # Filter stocks based on query
        if query:
            query = query.lower()
            
            # First, try to find exact matches for symbols (prioritize these)
            exact_symbol_matches = [
                stock for stock in all_stocks
                if stock['symbol'].lower() == query
            ]
            
            # Then find partial matches in symbols and names
            partial_matches = [
                stock for stock in all_stocks
                if (query in stock['symbol'].lower() or query in stock['name'].lower()) 
                and stock not in exact_symbol_matches
            ]
            
            # Combine results, with exact matches first
            filtered_stocks = exact_symbol_matches + partial_matches
            
            # If we have fewer than 5 results, try to search using yfinance
            if len(filtered_stocks) < 5:
                try:
                    # Try to get more results using yfinance search
                    # First check if it's a valid ticker
                    try:
                        ticker = yf.Ticker(query)
                        info = ticker.info
                        if 'shortName' in info or 'longName' in info:
                            name = info.get('shortName', info.get('longName', query))
                            symbol_result = {'symbol': query, 'name': name}
                            if symbol_result not in filtered_stocks:
                                filtered_stocks.append(symbol_result)
                    except:
                        pass
                    
                    # Try to search for Indian stocks if query might be for Indian market
                    if '.ns' not in query.lower() and len(query) >= 2:
                        indian_query = f"{query}.ns"
                        try:
                            ticker = yf.Ticker(indian_query)
                            info = ticker.info
                            if 'shortName' in info or 'longName' in info:
                                name = info.get('shortName', info.get('longName', indian_query))
                                symbol_result = {'symbol': indian_query.upper(), 'name': name}
                                if symbol_result not in filtered_stocks:
                                    filtered_stocks.append(symbol_result)
                        except:
                            pass
                except Exception as e:
                    print(f"Error searching with yfinance: {e}")
            
            return filtered_stocks[:10]  # Limit to 10 results
        
        # If no query, return a mix of popular US and Indian stocks
        popular_mix = us_stocks[:5] + indian_stocks[:5]
        return popular_mix
    
    except Exception as e:
        print(f"Error searching stocks: {e}")
        return []

def get_market_indices():
    """
    Get current data for major market indices
    
    Returns:
        Dictionary with index data
    """
    indices = {
        '^GSPC': 'S&P 500',
        '^DJI': 'Dow Jones',
        '^IXIC': 'NASDAQ',
        '^NSEI': 'Nifty 50',
        '^BSESN': 'Sensex'
    }
    
    result = {}
    
    # Fetch all indices at once for better performance
    try:
        tickers = yf.Tickers(' '.join(indices.keys()))
        for symbol, name in indices.items():
            try:
                ticker = tickers.tickers[symbol]
                hist = ticker.history(period='2d')
                
                if not hist.empty:
                    current = hist['Close'].iloc[-1]
                    prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else hist['Open'].iloc[-1]
                    change = current - prev_close
                    change_percent = (change / prev_close) * 100
                    
                    result[symbol] = {
                        'name': name,
                        'price': round(current, 2),
                        'change': round(change, 2),
                        'change_percent': round(change_percent, 2),
                        'volume': int(hist['Volume'].iloc[-1]),
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
            except Exception as e:
                print(f"Error processing data for {symbol}: {e}")
    except Exception as e:
        print(f"Error fetching market indices: {e}")
    
    return result

def get_watchlist_prices(symbols):
    """
    Get real-time prices for a list of stock symbols
    
    Args:
        symbols: List of stock ticker symbols
    
    Returns:
        Dictionary with real-time stock data
    """
    if not symbols:
        return {}
    
    result = {}
    
    # Process in batches of 10 symbols for better performance
    def process_batch(batch):
        batch_result = {}
        try:
            # Join symbols with space for yfinance
            symbols_str = ' '.join(batch)
            tickers = yf.Tickers(symbols_str)
            
            for symbol in batch:
                try:
                    ticker = tickers.tickers[symbol]
                    hist = ticker.history(period='2d')
                    
                    if not hist.empty:
                        current = hist['Close'].iloc[-1]
                        prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else hist['Open'].iloc[-1]
                        change = current - prev_close
                        change_percent = (change / prev_close) * 100
                        
                        # Get company name
                        info = ticker.info
                        name = info.get('shortName', info.get('longName', symbol))
                        
                        batch_result[symbol] = {
                            'symbol': symbol,
                            'name': name,
                            'price': round(current, 2),
                            'change': round(change, 2),
                            'change_percent': round(change_percent, 2),
                            'volume': int(hist['Volume'].iloc[-1]),
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                except Exception as e:
                    print(f"Error processing data for {symbol}: {e}")
                    batch_result[symbol] = {
                        'symbol': symbol,
                        'name': symbol,
                        'price': 0,
                        'change': 0,
                        'change_percent': 0,
                        'volume': 0,
                        'error': str(e)
                    }
        except Exception as e:
            print(f"Error fetching batch data: {e}")
        
        return batch_result
    
    # Split symbols into batches of 10
    batches = [symbols[i:i+10] for i in range(0, len(symbols), 10)]
    
    # Process batches in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        batch_results = list(executor.map(process_batch, batches))
    
    # Combine results
    for batch_result in batch_results:
        result.update(batch_result)
    
    return result

def get_portfolio_data(portfolio):
    """
    Get real-time data for a user's portfolio
    
    Args:
        portfolio: List of dictionaries with stock symbol and quantity
        Example: [{'symbol': 'AAPL', 'quantity': 10}, {'symbol': 'MSFT', 'quantity': 5}]
    
    Returns:
        Dictionary with portfolio performance data
    """
    if not portfolio:
        return {
            'total_value': 0,
            'daily_change': 0,
            'daily_change_percent': 0,
            'holdings': []
        }
    
    # Extract symbols from portfolio
    symbols = [item['symbol'] for item in portfolio]
    
    # Get real-time prices for all symbols
    prices_data = get_watchlist_prices(symbols)
    
    # Calculate portfolio metrics
    holdings = []
    total_value = 0
    total_daily_change = 0
    total_cost_basis = 0
    
    for item in portfolio:
        symbol = item['symbol']
        quantity = item['quantity']
        cost_basis = item.get('cost_basis', 0)
        
        if symbol in prices_data:
            price = prices_data[symbol]['price']
            change = prices_data[symbol]['change']
            
            value = price * quantity
            daily_change_value = change * quantity
            gain_loss = value - (cost_basis * quantity) if cost_basis else 0
            gain_loss_percent = (gain_loss / (cost_basis * quantity) * 100) if cost_basis and cost_basis > 0 else 0
            
            holdings.append({
                'symbol': symbol,
                'name': prices_data[symbol]['name'],
                'quantity': quantity,
                'price': price,
                'value': round(value, 2),
                'cost_basis': cost_basis,
                'daily_change': round(daily_change_value, 2),
                'daily_change_percent': prices_data[symbol]['change_percent'],
                'gain_loss': round(gain_loss, 2),
                'gain_loss_percent': round(gain_loss_percent, 2)
            })
            
            total_value += value
            total_daily_change += daily_change_value
            total_cost_basis += cost_basis * quantity
    
    # Calculate overall portfolio metrics
    total_daily_change_percent = (total_daily_change / total_value * 100) if total_value > 0 else 0
    total_gain_loss = total_value - total_cost_basis
    total_gain_loss_percent = (total_gain_loss / total_cost_basis * 100) if total_cost_basis > 0 else 0
    
    return {
        'total_value': round(total_value, 2),
        'daily_change': round(total_daily_change, 2),
        'daily_change_percent': round(total_daily_change_percent, 2),
        'total_gain_loss': round(total_gain_loss, 2),
        'total_gain_loss_percent': round(total_gain_loss_percent, 2),
        'holdings': sorted(holdings, key=lambda x: x['value'], reverse=True),
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

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
    try:
        import requests
        from bs4 import BeautifulSoup
        import re
        import json
        import time
        
        # Map of categories to their Yahoo Finance URLs
        category_urls = {
            'most-active': 'https://finance.yahoo.com/most-active',
            'trending': 'https://finance.yahoo.com/trending-tickers',
            'gainers': 'https://finance.yahoo.com/gainers',
            'losers': 'https://finance.yahoo.com/losers',
            '52-week-gainers': 'https://finance.yahoo.com/screener/predefined/strong_year_to_date_performers',
            '52-week-losers': 'https://finance.yahoo.com/screener/predefined/weak_year_to_date_performers'
        }
        
        if category not in category_urls:
            return {'error': f'Invalid category: {category}'}
        
        url = category_urls[category]
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        # Add a timestamp to avoid caching
        timestamp = int(time.time())
        url_with_timestamp = f"{url}?ts={timestamp}"
        
        response = requests.get(url_with_timestamp, headers=headers)
        if response.status_code != 200:
            return {'error': f'Failed to fetch data: HTTP {response.status_code}'}
        
        # Try to extract data from the page
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Method 1: Try to find the table directly
        table = soup.find('table')
        if not table:
            # Method 2: Look for the data in a script tag (Yahoo often stores data in JavaScript)
            script_data = None
            for script in soup.find_all('script'):
                if script.string and 'root.App.main' in script.string:
                    script_text = script.string
                    start_idx = script_text.find('root.App.main') + 16
                    # Find the JSON data
                    brace_count = 0
                    for i in range(start_idx, len(script_text)):
                        if script_text[i] == '{':
                            if brace_count == 0:
                                start_idx = i
                            brace_count += 1
                        elif script_text[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = i + 1
                                script_data = script_text[start_idx:end_idx]
                                break
                    break
            
            if not script_data:
                return {'error': 'Could not find stock data on the page'}
            
            try:
                # Parse the JSON data
                data = json.loads(script_data)
                
                # Extract the stock data from the JSON
                stocks_data = []
                
                # Navigate through the JSON structure to find the stock data
                # The exact path depends on Yahoo's structure, which can change
                if 'context' in data and 'dispatcher' in data:
                    stores = data.get('context', {}).get('dispatcher', {}).get('stores', {})
                    
                    # Try different paths where the stock data might be located
                    possible_paths = [
                        ['ScreenerResultsStore', 'results', 'rows'],
                        ['ScreenerCriteriaStore', 'results', 'rows'],
                        ['StreamDataStore', 'quoteData'],
                        ['QuoteSummaryStore', 'topGainers', 'rows'],
                        ['QuoteSummaryStore', 'topLosers', 'rows'],
                        ['QuoteSummaryStore', 'mostActives', 'rows']
                    ]
                    
                    stock_rows = None
                    for path in possible_paths:
                        current = stores
                        valid_path = True
                        for key in path:
                            if key in current:
                                current = current[key]
                            else:
                                valid_path = False
                                break
                        if valid_path and current:
                            stock_rows = current
                            break
                    
                    if stock_rows:
                        # Process the stock data
                        for item in stock_rows:
                            stock = {}
                            
                            # Extract data based on the structure
                            if isinstance(item, dict):
                                if 'symbol' in item:
                                    stock['symbol'] = item['symbol']
                                elif 'Symbol' in item:
                                    stock['symbol'] = item['Symbol']
                                
                                # Try different field names that might contain the company name
                                for name_field in ['shortName', 'longName', 'name', 'companyName', 'Company']:
                                    if name_field in item:
                                        stock['name'] = item[name_field]
                                        break
                                
                                # Extract price and other metrics
                                price_fields = ['regularMarketPrice', 'price', 'Price', 'lastPrice']
                                for field in price_fields:
                                    if field in item:
                                        if isinstance(item[field], dict) and 'raw' in item[field]:
                                            stock['price'] = item[field]['raw']
                                        else:
                                            stock['price'] = item[field]
                                        break
                                
                                # Extract change
                                change_fields = ['regularMarketChange', 'change', 'Change']
                                for field in change_fields:
                                    if field in item:
                                        if isinstance(item[field], dict) and 'raw' in item[field]:
                                            stock['change'] = item[field]['raw']
                                        else:
                                            stock['change'] = item[field]
                                        break
                                
                                # Extract change percent
                                pct_fields = ['regularMarketChangePercent', 'changePercent', 'ChangePct']
                                for field in pct_fields:
                                    if field in item:
                                        if isinstance(item[field], dict) and 'raw' in item[field]:
                                            stock['change_percent'] = item[field]['raw']
                                        else:
                                            stock['change_percent'] = item[field]
                                        break
                                
                                # Extract volume
                                vol_fields = ['regularMarketVolume', 'volume', 'Volume']
                                for field in vol_fields:
                                    if field in item:
                                        if isinstance(item[field], dict) and 'raw' in item[field]:
                                            stock['volume'] = item[field]['raw']
                                        else:
                                            stock['volume'] = item[field]
                                        break
                                
                                # Extract average volume
                                avg_vol_fields = ['averageDailyVolume3Month', 'avgVol', 'AvgVol']
                                for field in avg_vol_fields:
                                    if field in item:
                                        if isinstance(item[field], dict) and 'raw' in item[field]:
                                            stock['avg_volume'] = item[field]['raw']
                                        else:
                                            stock['avg_volume'] = item[field]
                                        break
                                
                                # Extract market cap
                                mcap_fields = ['marketCap', 'MarketCap']
                                for field in mcap_fields:
                                    if field in item:
                                        if isinstance(item[field], dict) and 'raw' in item[field]:
                                            stock['market_cap'] = item[field]['raw']
                                        else:
                                            stock['market_cap'] = item[field]
                                        break
                                
                                # Extract PE ratio
                                pe_fields = ['trailingPE', 'PE', 'peRatio']
                                for field in pe_fields:
                                    if field in item:
                                        if isinstance(item[field], dict) and 'raw' in item[field]:
                                            stock['pe_ratio'] = item[field]['raw']
                                        else:
                                            stock['pe_ratio'] = item[field]
                                        break
                                
                                # Extract 52-week change
                                week52_fields = ['52WeekChange', 'fiftyTwoWeekHighChangePercent']
                                for field in week52_fields:
                                    if field in item:
                                        if isinstance(item[field], dict) and 'raw' in item[field]:
                                            stock['week52_change'] = item[field]['raw']
                                        else:
                                            stock['week52_change'] = item[field]
                                        break
                            
                            # Only add stocks with at least symbol and price
                            if 'symbol' in stock and 'price' in stock:
                                stocks_data.append(stock)
                        
                        return stocks_data
            except Exception as json_error:
                print(f"Error parsing JSON data: {json_error}")
                return {'error': f'Error parsing JSON data: {json_error}'}
        
        # If we found a table, extract data from it
        if table:
            stocks_data = []
            rows = table.find('tbody').find_all('tr') if table.find('tbody') else table.find_all('tr')[1:]
            
            for row in rows:
                stock = {}
                cells = row.find_all('td')
                
                if len(cells) < 5:  # Need at least symbol, name, price, change, change%
                    continue
                
                # Extract symbol
                symbol_cell = cells[0].find('a')
                if symbol_cell:
                    stock['symbol'] = symbol_cell.text.strip()
                else:
                    continue  # Skip if no symbol
                
                # Extract name
                if len(cells) > 1:
                    stock['name'] = cells[1].text.strip()
                
                # Extract price
                if len(cells) > 2:
                    price_text = cells[2].text.strip().replace('$', '').replace(',', '')
                    try:
                        stock['price'] = float(price_text)
                    except ValueError:
                        stock['price'] = price_text
                
                # Extract change
                if len(cells) > 3:
                    change_text = cells[3].text.strip().replace('+', '').replace('$', '').replace(',', '')
                    try:
                        stock['change'] = float(change_text)
                    except ValueError:
                        stock['change'] = 0.0
                
                # Extract change percent
                if len(cells) > 4:
                    change_pct_text = cells[4].text.strip().replace('%', '').replace('+', '').replace('(', '').replace(')', '')
                    try:
                        stock['change_percent'] = float(change_pct_text)
                    except ValueError:
                        stock['change_percent'] = 0.0
                
                # Extract volume
                if len(cells) > 5:
                    volume_text = cells[5].text.strip().replace(',', '')
                    try:
                        stock['volume'] = int(volume_text)
                    except ValueError:
                        stock['volume'] = 0
                
                # Extract avg volume if available
                if len(cells) > 6:
                    avg_vol_text = cells[6].text.strip().replace(',', '')
                    try:
                        stock['avg_volume'] = int(avg_vol_text)
                    except ValueError:
                        stock['avg_volume'] = 0
                
                # Extract market cap if available
                if len(cells) > 7:
                    stock['market_cap'] = cells[7].text.strip()
                
                # Extract PE ratio if available
                if len(cells) > 8:
                    pe_text = cells[8].text.strip()
                    try:
                        stock['pe_ratio'] = float(pe_text)
                    except ValueError:
                        stock['pe_ratio'] = pe_text
                
                # Extract 52-week change if available
                if len(cells) > 9:
                    week52_text = cells[9].text.strip().replace('%', '')
                    try:
                        stock['week52_change'] = float(week52_text)
                    except ValueError:
                        stock['week52_change'] = week52_text
                
                stocks_data.append(stock)
            
            return stocks_data
        
        # If we couldn't extract data using either method
        return {'error': 'Could not extract stock data from the page'}
    
    except Exception as e:
        print(f"Error fetching {category} stocks: {e}")
        return {'error': str(e)}
