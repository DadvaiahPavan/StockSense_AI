"""
Yahoo Finance scraper using Playwright for reliable data extraction
"""
import asyncio
from playwright.async_api import async_playwright
import json
import time
import re
from datetime import datetime

async def scrape_yahoo_finance(category):
    """
    Scrape Yahoo Finance data using Playwright
    
    Args:
        category: Category of stocks to fetch (most-active, trending, gainers, losers, 52-week-gainers, 52-week-losers)
    
    Returns:
        List of dictionaries with stock data
    """
    # Map categories to Yahoo Finance URLs
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
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            
            page = await context.new_page()
            
            # Add timestamp to URL to avoid caching
            timestamp = int(time.time())
            url_with_timestamp = f"{url}?ts={timestamp}"
            
            # Navigate to the page
            await page.goto(url_with_timestamp, wait_until='networkidle')
            
            # Wait for the table to load
            await page.wait_for_selector('table', timeout=10000)
            
            # Extract data from the page
            stocks_data = await page.evaluate('''() => {
                const stocks = [];
                const table = document.querySelector('table');
                
                if (!table) return [];
                
                const rows = table.querySelectorAll('tbody tr');
                
                rows.forEach(row => {
                    const cells = row.querySelectorAll('td');
                    if (cells.length < 5) return;
                    
                    const stock = {};
                    
                    // Symbol - usually in the first column with a link
                    const symbolCell = cells[0].querySelector('a');
                    if (symbolCell) {
                        stock.symbol = symbolCell.textContent.trim();
                    } else {
                        return; // Skip if no symbol
                    }
                    
                    // Name - usually in the second column
                    if (cells.length > 1) {
                        stock.name = cells[1].textContent.trim();
                    }
                    
                    // Price - usually in the third column
                    if (cells.length > 2) {
                        const priceText = cells[2].textContent.trim().replace('$', '').replace(',', '');
                        stock.price = parseFloat(priceText) || priceText;
                    }
                    
                    // Change - usually in the fourth column
                    if (cells.length > 3) {
                        const changeText = cells[3].textContent.trim().replace('+', '').replace('$', '').replace(',', '');
                        stock.change = parseFloat(changeText) || 0;
                    }
                    
                    // Change Percent - usually in the fifth column
                    if (cells.length > 4) {
                        const changePctText = cells[4].textContent.trim().replace('%', '').replace('+', '').replace('(', '').replace(')', '');
                        stock.change_percent = parseFloat(changePctText) || 0;
                    }
                    
                    // Volume - usually in the sixth column
                    if (cells.length > 5) {
                        const volumeText = cells[5].textContent.trim().replace(',', '');
                        stock.volume = parseInt(volumeText) || 0;
                    }
                    
                    // Avg Volume - usually in the seventh column
                    if (cells.length > 6) {
                        const avgVolText = cells[6].textContent.trim().replace(',', '');
                        stock.avg_volume = parseInt(avgVolText) || 0;
                    }
                    
                    // Market Cap - usually in the eighth column
                    if (cells.length > 7) {
                        stock.market_cap = cells[7].textContent.trim();
                    }
                    
                    // PE Ratio - usually in the ninth column
                    if (cells.length > 8) {
                        const peText = cells[8].textContent.trim();
                        stock.pe_ratio = parseFloat(peText) || peText;
                    }
                    
                    // 52 Week Change - usually in the tenth column
                    if (cells.length > 9) {
                        const week52Text = cells[9].textContent.trim().replace('%', '');
                        stock.week52_change = parseFloat(week52Text) || week52Text;
                    }
                    
                    stocks.push(stock);
                });
                
                return stocks;
            }''')
            
            await browser.close()
            
            if not stocks_data:
                # Try alternate method - extract data from JSON in page
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                )
                
                page = await context.new_page()
                await page.goto(url_with_timestamp, wait_until='networkidle')
                
                # Extract JSON data from the page
                page_content = await page.content()
                json_match = re.search(r'root\.App\.main\s*=\s*(\{.*?\});\s*\(function', page_content, re.DOTALL)
                
                if json_match:
                    json_data = json_match.group(1)
                    try:
                        data = json.loads(json_data)
                        
                        # Extract stock data from JSON
                        stocks_data = []
                        
                        if 'context' in data and 'dispatcher' in data:
                            stores = data.get('context', {}).get('dispatcher', {}).get('stores', {})
                            
                            # Try different paths where stock data might be located
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
                                # Process stock data
                                for item in stock_rows:
                                    stock = {}
                                    
                                    # Extract data based on structure
                                    if isinstance(item, dict):
                                        if 'symbol' in item:
                                            stock['symbol'] = item['symbol']
                                        elif 'Symbol' in item:
                                            stock['symbol'] = item['Symbol']
                                        
                                        # Try different field names for company name
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
                    except Exception as json_error:
                        print(f"Error parsing JSON data: {json_error}")
                
                await browser.close()
            
            return stocks_data
    
    except Exception as e:
        print(f"Error scraping {category} stocks: {e}")
        return {'error': str(e)}

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
        # Run the async function
        return asyncio.run(scrape_yahoo_finance(category))
    except Exception as e:
        print(f"Error fetching {category} stocks: {e}")
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
