import yfinance as yf
from playwright.sync_api import sync_playwright
import pandas as pd
from datetime import datetime, timedelta
import time
import random
from bs4 import BeautifulSoup
import requests
import sys
import json

class StockDataFetcher:
    def __init__(self):
        self.news_sources = [
            {
                'name': 'Reuters Business',
                'url': 'https://www.reuters.com/business/',
                'method': 'playwright',
                'selectors': {
                    'articles': 'article.story',
                    'title': 'a[data-testid="Heading"]',
                    'link': 'a[data-testid="Heading"]',
                    'time': 'time'
                }
            },
            {
                'name': 'MarketWatch',
                'url': 'https://www.marketwatch.com/latest-news',
                'method': 'playwright',
                'selectors': {
                    'articles': 'div.article__content',
                    'title': 'h3.article__headline a',
                    'link': 'h3.article__headline a',
                    'time': 'span.article__timestamp'
                }
            },
            {
                'name': 'Financial Times',
                'url': 'https://www.ft.com/markets',
                'method': 'playwright',
                'selectors': {
                    'articles': 'div.o-teaser__content',
                    'title': 'a.js-teaser-heading-link',
                    'link': 'a.js-teaser-heading-link',
                    'time': 'time.o-teaser__timestamp'
                }
            }
        ]
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
        ]

    def fetch_market_indices(self):
        """Fetch real-time data for major market indices using yfinance"""
        print("Fetching market indices...")
        indices = {
            '^GSPC': {'name': 'S&P 500'},
            '^DJI': {'name': 'Dow Jones'},
            '^IXIC': {'name': 'NASDAQ'},
            '^RUT': {'name': 'Russell 2000'},
            '^FTSE': {'name': 'FTSE 100'},
            '^N225': {'name': 'Nikkei 225'},
            '^HSI': {'name': 'Hang Seng'}
        }

        try:
            # Fetch each index separately to ensure we get data
            for symbol in indices:
                try:
                    print(f"Fetching {symbol}...")
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period='2d')
                    
                    if len(hist) >= 2:
                        last_close = hist['Close'].iloc[-1]
                        prev_close = hist['Close'].iloc[-2]
                        change = round(last_close - prev_close, 2)
                        change_percent = round((change / prev_close) * 100, 2)
                    else:
                        # Fallback to current price if only 1 day data available
                        last_close = ticker.history(period='1d')['Close'].iloc[-1]
                        change = 0
                        change_percent = 0

                    indices[symbol].update({
                        'price': f"{last_close:,.2f}",
                        'change': f"{'+' if change >= 0 else ''}{change:.2f}",
                        'change_percent': f"{'+' if change_percent >= 0 else ''}{change_percent:.2f}",
                        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                except Exception as e:
                    print(f"Error processing {symbol}: {str(e)}", file=sys.stderr)
                    indices[symbol].update({
                        'price': "Error",
                        'change': "Error",
                        'change_percent': "Error",
                        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
        except Exception as e:
            print(f"Error fetching market indices: {str(e)}", file=sys.stderr)
            for symbol in indices:
                indices[symbol].update({
                    'price': "Unavailable",
                    'change': "Unavailable",
                    'change_percent': "Unavailable",
                    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })

        return indices

    def fetch_watchlist_prices(self, watchlist):
        """Fetch real-time prices for stocks in the watchlist using yfinance"""
        if not watchlist:
            return []

        watchlist_data = []

        try:
            # Fetch each stock separately to ensure we get proper change data
            for stock in watchlist:
                symbol = stock['symbol']
                try:
                    print(f"Fetching {symbol}...")
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period='2d')
                    
                    if len(hist) >= 2:
                        last_close = hist['Close'].iloc[-1]
                        prev_close = hist['Close'].iloc[-2]
                        change = round(last_close - prev_close, 2)
                        change_percent = round((change / prev_close) * 100, 2)
                    else:
                        # Fallback to current price if only 1 day data available
                        last_close = ticker.history(period='1d')['Close'].iloc[-1]
                        change = 0
                        change_percent = 0

                    watchlist_data.append({
                        'symbol': symbol,
                        'name': stock['name'],
                        'price': f"{last_close:,.2f}",
                        'change': f"{'+' if change >= 0 else ''}{change:.2f}",
                        'change_percent': f"{'+' if change_percent >= 0 else ''}{change_percent:.2f}",
                        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                except Exception as e:
                    print(f"Error processing {symbol}: {str(e)}", file=sys.stderr)
                    watchlist_data.append({
                        'symbol': symbol,
                        'name': stock['name'],
                        'price': "Error",
                        'change': "Error",
                        'change_percent': "Error",
                        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
        except Exception as e:
            print(f"Error fetching watchlist prices: {str(e)}", file=sys.stderr)
            for stock in watchlist:
                watchlist_data.append({
                    'symbol': stock['symbol'],
                    'name': stock['name'],
                    'price': "Unavailable",
                    'change': "Unavailable",
                    'change_percent': "Unavailable",
                    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })

        return watchlist_data

    def fetch_portfolio_data(self, portfolio):
        """Fetch real-time portfolio data using yfinance"""
        if not portfolio:
            return {
                'current_value': 0,
                'total_change': 0,
                'percent_change': 0,
                'history': [],
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

        portfolio_value = 0
        portfolio_cost = 0
        stocks_data = {}

        try:
            # Fetch each stock in portfolio
            for symbol, holdings in portfolio.items():
                try:
                    print(f"Fetching portfolio stock {symbol}...")
                    ticker = yf.Ticker(symbol)
                    current_price = ticker.history(period='1d')['Close'].iloc[-1]
                    
                    position_value = current_price * holdings['shares']
                    position_cost = holdings['avg_price'] * holdings['shares']
                    
                    portfolio_value += position_value
                    portfolio_cost += position_cost
                    
                    stocks_data[symbol] = {
                        'current_price': current_price,
                        'position_value': position_value,
                        'position_cost': position_cost,
                        'gain_loss': position_value - position_cost,
                        'gain_loss_pct': ((position_value - position_cost) / position_cost) * 100
                    }
                except Exception as e:
                    print(f"Error processing portfolio stock {symbol}: {str(e)}", file=sys.stderr)
                    stocks_data[symbol] = {
                        'current_price': "Error",
                        'position_value': "Error",
                        'position_cost': "Error",
                        'gain_loss': "Error",
                        'gain_loss_pct': "Error"
                    }

            # Calculate portfolio metrics
            total_change = portfolio_value - portfolio_cost
            percent_change = (total_change / portfolio_cost) * 100 if portfolio_cost != 0 else 0

            # Generate historical data (last 30 days)
            history = self._generate_portfolio_history(portfolio)

            return {
                'current_value': round(portfolio_value, 2),
                'total_change': round(total_change, 2),
                'percent_change': round(percent_change, 2),
                'stocks': stocks_data,
                'history': history,
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

        except Exception as e:
            print(f"Error fetching portfolio data: {str(e)}", file=sys.stderr)
            return {
                'current_value': "Unavailable",
                'total_change': "Unavailable",
                'percent_change': "Unavailable",
                'stocks': {},
                'history': [],
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

    def _generate_portfolio_history(self, portfolio):
        """Generate historical portfolio data for the last 30 days"""
        if not portfolio:
            return []

        symbols = list(portfolio.keys())
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        history = []

        try:
            # Create date index first
            date_range = pd.date_range(start_date, end_date)
            history = [{'date': date.strftime('%Y-%m-%d'), 'value': 0} for date in date_range]
            
            # Fetch historical data for each stock
            for symbol, holdings in portfolio.items():
                try:
                    print(f"Fetching historical data for {symbol}...")
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(start=start_date.strftime('%Y-%m-%d'), 
                                         end=end_date.strftime('%Y-%m-%d'))
                    
                    for date, row in hist.iterrows():
                        date_str = date.strftime('%Y-%m-%d')
                        daily_value = row['Close'] * holdings['shares']
                        
                        # Find entry for this date
                        entry = next((x for x in history if x['date'] == date_str), None)
                        if entry:
                            entry['value'] += daily_value
                except Exception as e:
                    print(f"Error processing historical data for {symbol}: {str(e)}", file=sys.stderr)
                    continue
            
            # Format dates and sort
            for entry in history:
                entry['date'] = datetime.strptime(entry['date'], '%Y-%m-%d').strftime('%b %d')
            
            return history
        except Exception as e:
            print(f"Error generating portfolio history: {str(e)}", file=sys.stderr)
            return []

    def scrape_market_news(self):
        """Scrape market news from reliable sources using Playwright"""
        news_items = []
        
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=random.choice(self.user_agents),
                viewport={'width': 1280, 'height': 720},
                java_script_enabled=True
            )
            
            for source in self.news_sources:
                try:
                    print(f"Scraping news from {source['name']}...")
                    page = context.new_page()
                    
                    # Set longer timeout and navigate
                    page.set_default_timeout(30000)
                    page.goto(source['url'], wait_until="domcontentloaded")
                    
                    # Wait for content with multiple strategies
                    try:
                        page.wait_for_selector(source['selectors']['articles'], timeout=15000)
                    except:
                        print(f"Primary selector not found, trying fallback...")
                        page.wait_for_selector('article', timeout=10000)
                    
                    # Get page content
                    content = page.content()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Find articles with multiple selector strategies
                    articles = []
                    selectors_to_try = [
                        source['selectors']['articles'],
                        'article',
                        'div[class*="article"]',
                        'div[class*="card"]',
                        'li[class*="item"]'
                    ]
                    
                    for selector in selectors_to_try:
                        articles = soup.select(selector)
                        if articles:
                            break
                    
                    for article in articles[:5]:  # Limit to 5 per source
                        try:
                            # Extract title with multiple fallbacks
                            title = None
                            for selector in [source['selectors']['title'], 'h3', 'h2', 'h1', 'a[class*="title"]']:
                                title_elem = article.select_one(selector)
                                if title_elem:
                                    title_text = title_elem.get_text(strip=True)
                                    if title_text and len(title_text) > 10:  # Minimum length check
                                        title = title_text
                                        break
                            
                            if not title:
                                continue
                                
                            # Extract link with multiple fallbacks
                            link = "#"
                            for selector in [source['selectors']['link'], 'a', 'a[href]']:
                                link_elem = article.select_one(selector)
                                if link_elem and 'href' in link_elem.attrs:
                                    link = link_elem['href']
                                    if not link.startswith('http'):
                                        link = requests.compat.urljoin(source['url'], link)
                                    break
                            
                            # Extract time with multiple fallbacks
                            time_text = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            for selector in [source['selectors']['time'], 'time', 'span[class*="time"]']:
                                time_elem = article.select_one(selector)
                                if time_elem:
                                    time_text = time_elem.get_text(strip=True)
                                    break
                            
                            news_items.append({
                                'title': title,
                                'source': source['name'],
                                'published': time_text,
                                'url': link
                            })
                        except Exception as e:
                            print(f"Error parsing article from {source['name']}: {str(e)}", file=sys.stderr)
                            continue
                    
                    page.close()
                except Exception as e:
                    print(f"Error scraping {source['name']}: {str(e)}", file=sys.stderr)
                    continue
            
            browser.close()
        
        # Sort news by recency
        news_items.sort(key=lambda x: self._parse_news_date(x['published']), reverse=True)
        
        return news_items[:10] if news_items else [
            {
                'title': 'Market news currently unavailable - please try again later',
                'source': 'Stock Dashboard',
                'published': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'url': '#'
            }
        ]

    def _parse_news_date(self, date_str):
        """Convert various date formats to timestamp for sorting"""
        try:
            # Try common date formats
            for fmt in ('%Y-%m-%d %H:%M:%S', '%b %d, %Y', '%B %d, %Y', '%m/%d/%Y', '%H:%M %p', '%I:%M %p'):
                try:
                    return datetime.strptime(date_str, fmt).timestamp()
                except:
                    continue
            
            # Try to extract time ago (e.g., "5 hours ago")
            if 'minute' in date_str.lower():
                mins = int(''.join(filter(str.isdigit, date_str)))
                return (datetime.now() - timedelta(minutes=mins)).timestamp()
            elif 'hour' in date_str.lower():
                hours = int(''.join(filter(str.isdigit, date_str)))
                return (datetime.now() - timedelta(hours=hours)).timestamp()
            elif 'day' in date_str.lower():
                days = int(''.join(filter(str.isdigit, date_str)))
                return (datetime.now() - timedelta(days=days)).timestamp()
            
            return datetime.now().timestamp()  # Default to now if we can't parse
        except:
            return datetime.now().timestamp()

    def get_dashboard_data(self, watchlist=None, portfolio=None):
        """Get all data needed for the dashboard"""
        if watchlist is None:
            watchlist = []
        if portfolio is None:
            portfolio = {}
        
        return {
            'market_indices': self.fetch_market_indices(),
            'watchlist': self.fetch_watchlist_prices(watchlist),
            'portfolio': self.fetch_portfolio_data(portfolio),
            'market_news': self.scrape_market_news(),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

def main():
    print("Starting Stock Data Fetcher...")
    fetcher = StockDataFetcher()
    
    # Sample data with more realistic values
    sample_watchlist = [
        {'symbol': 'AAPL', 'name': 'Apple Inc.'},
        {'symbol': 'MSFT', 'name': 'Microsoft Corporation'},
        {'symbol': 'GOOGL', 'name': 'Alphabet Inc.'},
        {'symbol': 'AMZN', 'name': 'Amazon.com Inc.'},
        {'symbol': 'TSLA', 'name': 'Tesla Inc.'}
    ]
    
    # Updated with more realistic portfolio values
    sample_portfolio = {
        'AAPL': {'shares': 10, 'avg_price': 170.00},
        'MSFT': {'shares': 5, 'avg_price': 300.00},
        'GOOGL': {'shares': 3, 'avg_price': 140.00}
    }
    
    print("\nFetching real-time dashboard data...")
    start_time = time.time()
    
    try:
        dashboard_data = fetcher.get_dashboard_data(sample_watchlist, sample_portfolio)
        
        print(f"\nData fetched in {time.time() - start_time:.2f} seconds")
        print("\nMarket Indices:")
        for symbol, data in dashboard_data['market_indices'].items():
            print(f"{data['name']} ({symbol}): {data['price']} ({data['change']}, {data['change_percent']}%)")
        
        print("\nWatchlist:")
        for stock in dashboard_data['watchlist']:
            print(f"{stock['symbol']}: {stock['price']} ({stock['change']}, {stock['change_percent']}%)")
        
        print("\nPortfolio Summary:")
        portfolio = dashboard_data['portfolio']
        print(f"Current Value: ${portfolio['current_value']:,.2f}")
        print(f"Total Change: ${portfolio['total_change']:+,.2f} ({portfolio['percent_change']:+,.2f}%)")
        
        print("\nLatest Market News:")
        if dashboard_data['market_news'][0]['title'] == 'Market news currently unavailable':
            print("Could not fetch market news - websites may have changed their structure")
        else:
            for i, news in enumerate(dashboard_data['market_news'][:5], 1):
                print(f"{i}. {news['title']} ({news['source']} - {news['published']})")
    except Exception as e:
        print(f"\nError in main execution: {str(e)}", file=sys.stderr)

if __name__ == "__main__":
    main()