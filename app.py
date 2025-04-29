import os
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import json
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
from dotenv import load_dotenv
import time
import groq
import numpy as np
import pickle
import uuid
import logging
import threading
import concurrent.futures
from functools import lru_cache

# Import services
from services.stock_service import get_stock_data, get_stock_info, search_stocks, get_market_indices, get_watchlist_prices, get_portfolio_data
from services.yahoo_scraper import get_yahoo_market_stocks
from services.ai_service import analyze_stock_movement, chat_with_ai
from services.strategy_service import backtest_strategy, get_predefined_strategies
from services.scraper_service import get_market_news, get_social_sentiment

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-dev-key')
app.config['DATABASE'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stocksense.db')

# Setup login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database initialization
def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with app.app_context():
        conn = get_db_connection()
        with open('schema.sql') as f:
            conn.executescript(f.read())
        conn.commit()
        conn.close()

# User loader for Flask-Login
class User:
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False
    
    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    
    if user:
        return User(user['id'], user['username'], user['email'])
    return None

# Create a simple in-memory cache with expiration
stock_data_cache = {}
cache_lock = threading.Lock()

def cache_with_timeout(seconds=300):
    """Cache decorator with timeout"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            with cache_lock:
                if cache_key in stock_data_cache:
                    cached_data, timestamp = stock_data_cache[cache_key]
                    if datetime.now().timestamp() - timestamp < seconds:
                        return cached_data
            
            # If not in cache or expired, call the function
            result = func(*args, **kwargs)
            
            # Update cache
            with cache_lock:
                stock_data_cache[cache_key] = (result, datetime.now().timestamp())
            
            return result
        return wrapper
    return decorator

# Apply cache to expensive operations
@cache_with_timeout(seconds=300)  # Cache for 5 minutes
def cached_get_yahoo_market_stocks(category):
    return get_yahoo_market_stocks(category)

# Thread worker to load data for dashboard
def load_dashboard_data():
    try:
        # Get market indices data
        indices = get_market_indices()
        
        # Get various categories of stock data in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            # Submit all tasks
            most_active_future = executor.submit(cached_get_yahoo_market_stocks, 'most-active')
            trending_future = executor.submit(cached_get_yahoo_market_stocks, 'trending')
            gainers_future = executor.submit(cached_get_yahoo_market_stocks, 'gainers')
            losers_future = executor.submit(cached_get_yahoo_market_stocks, 'losers')
            week52_gainers_future = executor.submit(cached_get_yahoo_market_stocks, '52-week-gainers')
            week52_losers_future = executor.submit(cached_get_yahoo_market_stocks, '52-week-losers')
            
            # Get results as they complete
            most_active = most_active_future.result()
            trending = trending_future.result()
            gainers = gainers_future.result()
            losers = losers_future.result()
            week52_gainers = week52_gainers_future.result()
            week52_losers = week52_losers_future.result()
        
        # Process stocks to ensure numeric values are of correct type
        for stock_list in [most_active, trending, gainers, losers, week52_gainers, week52_losers]:
            if isinstance(stock_list, list):
                for stock in stock_list:
                    try:
                        # Convert price to float
                        if 'price' in stock:
                            stock['price'] = float(stock['price']) if stock['price'] not in ('N/A', '') else 0.0
                        
                        # Convert change to float
                        if 'change' in stock:
                            stock['change'] = float(stock['change']) if stock['change'] not in ('N/A', '') else 0.0
                        
                        # Convert change_percent to float
                        if 'change_percent' in stock:
                            stock['change_percent'] = float(stock['change_percent']) if stock['change_percent'] not in ('N/A', '') else 0.0
                    except (ValueError, TypeError) as e:
                        app.logger.error(f"Error converting stock data values: {str(e)}")
        
        return {
            'indices': indices,
            'most_active': most_active,
            'trending': trending,
            'gainers': gainers,
            'losers': losers,
            'week52_gainers': week52_gainers,
            'week52_losers': week52_losers
        }
    except Exception as e:
        app.logger.error(f"Error loading dashboard data: {str(e)}")
        return {}

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        
        if user:
            flash('Email already exists')
            conn.close()
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        conn.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                    (username, email, hashed_password))
        conn.commit()
        
        user_id = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()[0]
        conn.close()
        
        user = User(user_id, username, email)
        login_user(user)
        
        # Add a short delay to show loading animation
        time.sleep(0.7)  # Slightly longer for registration which typically takes more time
        
        return redirect(url_for('dashboard'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        
        if user and check_password_hash(user['password'], password):
            user_obj = User(user['id'], user['username'], user['email'])
            login_user(user_obj)
            conn.close()
            
            # Add a short delay to show loading animation (this is optional but provides better UX)
            # Delay is server-side to ensure the loading animation is properly displayed
            time.sleep(0.5)  # Half-second delay
            
            return redirect(url_for('dashboard'))
        
        flash('Invalid email or password')
        conn.close()
        return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get user's watchlist items
    conn = get_db_connection()
    watchlist_items = conn.execute('SELECT * FROM watchlist WHERE user_id = ?', (current_user.id,)).fetchall()
    conn.close()
    
    # Get real-time watchlist prices
    watchlist_data = []
    if watchlist_items:
        # Extract symbols from watchlist items
        symbols = [item['symbol'] for item in watchlist_items]
        
        # Get real-time data for all symbols at once
        try:
            watchlist_prices = get_watchlist_prices(symbols)
            
            # Combine database and real-time data
            for item in watchlist_items:
                symbol = item['symbol']
                if symbol in watchlist_prices:
                    stock_data = watchlist_prices[symbol]
                    watchlist_data.append({
                        'id': item['id'],
                        'symbol': symbol,
                        'name': item['name'],
                        'price': stock_data.get('price', 0),
                        'change': stock_data.get('change', 0),
                        'change_percent': stock_data.get('change_percent', 0),
                        'volume': stock_data.get('volume', 'N/A'),
                        'market_cap': stock_data.get('market_cap', 'N/A')
                    })
                else:
                    # Fallback if real-time data is not available
                    watchlist_data.append({
                        'id': item['id'],
                        'symbol': symbol,
                        'name': item['name'],
                        'price': 'N/A',
                        'change': 0,
                        'change_percent': 0,
                        'volume': 'N/A',
                        'market_cap': 'N/A'
                    })
        except Exception as e:
            app.logger.error(f"Error fetching watchlist prices: {str(e)}")
            # Fallback to basic data
            for item in watchlist_items:
                watchlist_data.append({
                    'id': item['id'],
                    'symbol': item['symbol'],
                    'name': item['name'],
                    'price': 'N/A',
                    'change': 0,
                    'change_percent': 0,
                    'volume': 'N/A',
                    'market_cap': 'N/A'
                })
    
    # Get latest market news
    try:
        news = get_market_news('market news', limit=5)
    except Exception as e:
        app.logger.error(f"Error fetching news: {str(e)}")
        news = []
    
    # Use cached/preloaded market data
    try:
        # Generate a unique key for this user's session
        cache_key = f"dashboard_data:{current_user.id}"
        
        with cache_lock:
            if cache_key in stock_data_cache:
                market_data, timestamp = stock_data_cache[cache_key]
                # Use cached data if less than 5 minutes old
                if datetime.now().timestamp() - timestamp < 300:
                    # Add a small delay for the loading animation
                    time.sleep(0.5)
                    return render_template(
                        'dashboard.html',
                        indices=market_data['indices'],
                        watchlist=watchlist_data,
                        news=news,
                        most_active=market_data['most_active'],
                        trending=market_data['trending'],
                        gainers=market_data['gainers'],
                        losers=market_data['losers'],
                        week52_gainers=market_data['week52_gainers'],
                        week52_losers=market_data['week52_losers']
                    )
        
        # If no cached data or data is stale, load fresh data
        market_data = load_dashboard_data()
        
        # Cache the market data
        with cache_lock:
            stock_data_cache[cache_key] = (market_data, datetime.now().timestamp())
        
    except Exception as e:
        app.logger.error(f"Error with dashboard cache: {str(e)}")
        # Fallback to direct loading
        market_data = {
            'indices': get_market_indices(),
            'most_active': cached_get_yahoo_market_stocks('most-active'),
            'trending': cached_get_yahoo_market_stocks('trending'),
            'gainers': cached_get_yahoo_market_stocks('gainers'),
            'losers': cached_get_yahoo_market_stocks('losers'),
            'week52_gainers': cached_get_yahoo_market_stocks('52-week-gainers'),
            'week52_losers': cached_get_yahoo_market_stocks('52-week-losers')
        }
    
    # Add a small delay to ensure the loading animation is visible
    time.sleep(0.5)
    
    return render_template(
        'dashboard.html',
        indices=market_data['indices'],
        watchlist=watchlist_data,
        news=news,
        most_active=market_data['most_active'],
        trending=market_data['trending'],
        gainers=market_data['gainers'],
        losers=market_data['losers'],
        week52_gainers=market_data.get('week52_gainers', []),
        week52_losers=market_data.get('week52_losers', [])
    )

@app.route('/stock/<symbol>')
@login_required
def stock_details(symbol):
    # Get stock information
    stock_info = get_stock_info(symbol)
    
    # Get historical data for charts
    historical_data = get_stock_data(symbol, period='1y', interval='1d')
    
    return render_template('stock_details.html', 
                          symbol=symbol,
                          stock_info=stock_info,
                          historical_data=json.dumps(historical_data))

@app.route('/stock_search')
def stock_search():
    """Stock search page with autocomplete and real-time data"""
    return render_template('stock_search.html')

@app.route('/api/stock/search')
def api_stock_search():
    query = request.args.get('query', '')
    results = search_stocks(query)
    return jsonify(results)

@app.route('/api/stock/info')
def api_stock_info():
    symbol = request.args.get('symbol', '')
    if not symbol:
        return jsonify({'error': 'Symbol is required'})
    
    # Try to get stock info
    try:
        info = get_stock_info(symbol)
        
        # Check if we got an error back
        if 'error' in info and info['error'] != symbol:
            # Try with .NS suffix for Indian stocks if not already present
            if not symbol.endswith('.NS') and not symbol.endswith('.ns'):
                try:
                    indian_symbol = f"{symbol}.NS"
                    print(f"Trying with Indian stock suffix: {indian_symbol}")
                    info = get_stock_info(indian_symbol)
                    if 'error' not in info or info['error'] == indian_symbol:
                        symbol = indian_symbol  # Update symbol for day change calculation
                except Exception as e:
                    print(f"Error getting Indian stock info: {e}")
        
        # Add day change and percentage if available
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='2d')
            if len(hist) >= 2:
                prev_close = hist['Close'].iloc[-2]
                current = hist['Close'].iloc[-1]
                day_change = current - prev_close
                day_change_percent = (day_change / prev_close) * 100
                info['day_change'] = day_change
                info['day_change_percent'] = day_change_percent
        except Exception as e:
            print(f"Error calculating day change: {e}")
        
        return jsonify(info)
    except Exception as e:
        print(f"Error in stock info API: {e}")
        return jsonify({
            'error': f"Could not retrieve information for {symbol}",
            'symbol': symbol,
            'name': symbol
        })

@app.route('/api/stock/data')
def api_stock_data():
    symbol = request.args.get('symbol', '')
    period = request.args.get('period', '1y')
    interval = request.args.get('interval', '1d')
    
    data = get_stock_data(symbol, period, interval)
    return jsonify(data)

@app.route('/api/watchlist/add', methods=['POST'])
@login_required
def api_add_to_watchlist():
    data = request.json
    symbol = data.get('symbol')
    name = data.get('name')
    
    conn = get_db_connection()
    existing = conn.execute('SELECT * FROM watchlist WHERE user_id = ? AND symbol = ?', 
                          (current_user.id, symbol)).fetchone()
    
    if not existing:
        conn.execute('INSERT INTO watchlist (user_id, symbol, name) VALUES (?, ?, ?)',
                    (current_user.id, symbol, name))
        conn.commit()
    
    conn.close()
    return jsonify({'success': True})

@app.route('/api/watchlist/remove', methods=['POST'])
@login_required
def api_remove_from_watchlist():
    data = request.json
    symbol = data.get('symbol')
    
    if not symbol:
        return jsonify({'success': False, 'error': 'No symbol provided'}), 400
    
    try:
        conn = get_db_connection()
        # First check if the item exists
        item = conn.execute('SELECT id FROM watchlist WHERE user_id = ? AND symbol = ?', 
                          (current_user.id, symbol)).fetchone()
        
        if not item:
            conn.close()
            return jsonify({'success': False, 'error': 'Item not found in watchlist'}), 404
        
        # Delete the item
        conn.execute('DELETE FROM watchlist WHERE user_id = ? AND symbol = ?', 
                    (current_user.id, symbol))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'Removed {symbol} from watchlist'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/strategy-builder')
@login_required
def strategy_builder():
    predefined_strategies = get_predefined_strategies()
    return render_template('strategy_builder.html', strategies=predefined_strategies)

@app.route('/api/backtest', methods=['POST'])
@login_required
def api_backtest_strategy():
    data = request.json
    symbol = data.get('symbol')
    strategy = data.get('strategy')
    parameters = data.get('parameters', {})
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    results = backtest_strategy(symbol, strategy, parameters, start_date, end_date)
    return jsonify(results)

@app.route('/api/strategy/save', methods=['POST'])
@login_required
def api_save_strategy():
    try:
        data = request.json
        name = data.get('name')
        symbol = data.get('symbol')
        strategy_type = data.get('strategy_type')
        parameters = json.dumps(data.get('parameters', {}))
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        metrics = json.dumps(data.get('metrics', {}))
        
        if not name or not symbol or not strategy_type:
            return jsonify({'success': False, 'error': 'Missing required fields'})
        
        conn = get_db_connection()
        
        # Check if strategy with the same name already exists for this user
        existing = conn.execute(
            'SELECT id FROM saved_strategies WHERE user_id = ? AND name = ?', 
            (current_user.id, name)
        ).fetchone()
        
        if existing:
            conn.execute(
                '''UPDATE saved_strategies 
                   SET symbol = ?, strategy_type = ?, parameters = ?, 
                       start_date = ?, end_date = ?, metrics = ?, updated_at = ?
                   WHERE id = ?''',
                (symbol, strategy_type, parameters, start_date, end_date, metrics, 
                 datetime.now().strftime('%Y-%m-%d %H:%M:%S'), existing['id'])
            )
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Strategy updated successfully'})
        else:
            conn.execute(
                '''INSERT INTO saved_strategies 
                   (user_id, name, symbol, strategy_type, parameters, start_date, end_date, metrics, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (current_user.id, name, symbol, strategy_type, parameters, start_date, end_date, metrics,
                 datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Strategy saved successfully'})
    
    except Exception as e:
        print(f"Error saving strategy: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/stock-analysis/<symbol>')
@login_required
def stock_analysis(symbol):
    # Get stock information
    stock_info = get_stock_info(symbol)
    
    # Get AI analysis
    analysis = analyze_stock_movement(symbol)
    
    # Add prediction data that the template is expecting
    analysis['current_price'] = stock_info.get('price', 0)
    analysis['prediction_7d'] = {
        'direction': 'up' if analysis.get('sentiment') == 'bullish' else 'down' if analysis.get('sentiment') == 'bearish' else 'neutral',
        'confidence': f"{int(analysis.get('confidence', 0.5) * 100)}%",
        'target_price': round(stock_info.get('price', 0) * (1 + (0.05 if analysis.get('sentiment') == 'bullish' else -0.05 if analysis.get('sentiment') == 'bearish' else 0)), 2)
    }
    analysis['prediction_30d'] = {
        'direction': 'up' if analysis.get('sentiment') == 'bullish' else 'down' if analysis.get('sentiment') == 'bearish' else 'neutral',
        'confidence': f"{int(analysis.get('confidence', 0.5) * 90)}%",
        'target_price': round(stock_info.get('price', 0) * (1 + (0.12 if analysis.get('sentiment') == 'bullish' else -0.12 if analysis.get('sentiment') == 'bearish' else 0)), 2)
    }
    analysis['technical_analysis'] = f"Based on technical indicators, {symbol} is showing a {analysis.get('sentiment')} trend. The stock has been performing {'positively' if analysis.get('sentiment') == 'bullish' else 'negatively' if analysis.get('sentiment') == 'bearish' else 'with mixed signals'}."
    analysis['reasoning'] = f"Our AI analysis considers multiple factors including price movement, volume trends, and technical indicators. {symbol} has shown {'strength' if analysis.get('sentiment') == 'bullish' else 'weakness' if analysis.get('sentiment') == 'bearish' else 'stability'} in recent trading sessions, leading to our current outlook."
    analysis['risk_assessment'] = 'Medium' if analysis.get('confidence', 0.5) < 0.7 else ('Low' if analysis.get('sentiment') == 'bullish' else 'High')
    
    return render_template('stock_analysis.html',
                          symbol=symbol,
                          stock_info=stock_info,
                          analysis=analysis)

@app.route('/chatbot')
@login_required
def chatbot():
    return render_template('chatbot.html')

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    data = request.json
    message = data.get('message')
    
    response = chat_with_ai(message)
    return jsonify({'response': response})

@app.route('/stock-predictor')
@login_required
def stock_predictor():
    """Stock predictor page with AI-powered predictions."""
    return render_template('stock_predictor.html')

@app.route('/api/predict-stock/<symbol>')
@login_required
def api_predict_stock(symbol):
    """API endpoint to predict stock movement and generate explanation using Groq API."""
    try:
        # Check if it's an Indian stock and add .NS suffix if needed
        is_indian_stock = False
        if '.' not in symbol and any(bank in symbol.upper() for bank in ['HDFC', 'ICICI', 'SBI', 'KOTAK', 'AXIS', 'TCS', 'INFY', 'RELIANCE']):
            original_symbol = symbol
            symbol = f"{symbol}.NS"
            is_indian_stock = True
            print(f"Detected Indian stock. Trying with NS suffix: {symbol}")
        
        # Get stock data
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="120d")  # Get more historical data for better prediction
        
        if hist.empty and is_indian_stock and '.' not in original_symbol:
            # Try with .BO suffix (Bombay Stock Exchange) if NS didn't work
            symbol = f"{original_symbol}.BO"
            print(f"NS suffix didn't work. Trying with BO suffix: {symbol}")
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="120d")
        
        if hist.empty:
            return jsonify({
                "error": f"No data available for {symbol}. For Indian stocks, try adding .NS or .BO suffix."
            })
        
        # Prepare historical data for visualization
        dates = hist.index.strftime('%Y-%m-%d').tolist()
        historical_prices = hist['Close'].tolist()
        
        # Calculate technical indicators
        hist['SMA20'] = hist['Close'].rolling(window=20).mean()
        hist['SMA50'] = hist['Close'].rolling(window=50).mean()
        hist['SMA200'] = hist['Close'].rolling(window=200).mean()
        
        # Calculate RSI
        delta = hist['Close'].diff()
        gain = delta.where(delta > 0, 0).fillna(0)
        loss = -delta.where(delta < 0, 0).fillna(0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss.replace(0, 0.001)  # Avoid division by zero
        hist['RSI'] = 100 - (100 / (1 + rs))
        
        # Calculate MACD
        hist['EMA12'] = hist['Close'].ewm(span=12, adjust=False).mean()
        hist['EMA26'] = hist['Close'].ewm(span=26, adjust=False).mean()
        hist['MACD'] = hist['EMA12'] - hist['EMA26']
        hist['Signal'] = hist['MACD'].ewm(span=9, adjust=False).mean()
        
        # Calculate Bollinger Bands
        hist['Middle Band'] = hist['Close'].rolling(window=20).mean()
        hist['STD'] = hist['Close'].rolling(window=20).std()
        hist['Upper Band'] = hist['Middle Band'] + (hist['STD'] * 2)
        hist['Lower Band'] = hist['Middle Band'] - (hist['STD'] * 2)
        
        # Recent values for analysis
        current_price = hist['Close'].iloc[-1]
        prev_price = hist['Close'].iloc[-2]
        sma20 = hist['SMA20'].iloc[-1]
        sma50 = hist['SMA50'].iloc[-1]
        sma200 = hist['SMA200'].iloc[-1] if len(hist) >= 200 else None
        rsi = hist['RSI'].iloc[-1]
        macd = hist['MACD'].iloc[-1]
        signal = hist['Signal'].iloc[-1]
        upper_band = hist['Upper Band'].iloc[-1]
        lower_band = hist['Lower Band'].iloc[-1]
        
        # Determine prediction based on technical indicators
        prediction_factors = []
        
        # RSI signals
        if rsi > 70:
            prediction_factors.append({"factor": "RSI", "signal": "bearish", "value": rsi, "weight": 0.3})
        elif rsi < 30:
            prediction_factors.append({"factor": "RSI", "signal": "bullish", "value": rsi, "weight": 0.3})
        else:
            prediction_factors.append({"factor": "RSI", "signal": "neutral", "value": rsi, "weight": 0.1})
        
        # Moving average signals
        if current_price > sma20 and sma20 > sma50:
            prediction_factors.append({"factor": "Moving Averages", "signal": "bullish", "value": f"Price > SMA20 > SMA50", "weight": 0.25})
        elif current_price < sma20 and sma20 < sma50:
            prediction_factors.append({"factor": "Moving Averages", "signal": "bearish", "value": f"Price < SMA20 < SMA50", "weight": 0.25})
        else:
            prediction_factors.append({"factor": "Moving Averages", "signal": "neutral", "value": f"Mixed signals", "weight": 0.1})
        
        # MACD signals
        if macd > signal and macd > 0:
            prediction_factors.append({"factor": "MACD", "signal": "bullish", "value": f"MACD({macd:.2f}) > Signal({signal:.2f})", "weight": 0.25})
        elif macd < signal and macd < 0:
            prediction_factors.append({"factor": "MACD", "signal": "bearish", "value": f"MACD({macd:.2f}) < Signal({signal:.2f})", "weight": 0.25})
        else:
            prediction_factors.append({"factor": "MACD", "signal": "neutral", "value": f"MACD({macd:.2f}), Signal({signal:.2f})", "weight": 0.1})
        
        # Bollinger Bands signals
        if current_price > upper_band:
            prediction_factors.append({"factor": "Bollinger Bands", "signal": "bearish", "value": f"Price({current_price:.2f}) > Upper({upper_band:.2f})", "weight": 0.2})
        elif current_price < lower_band:
            prediction_factors.append({"factor": "Bollinger Bands", "signal": "bullish", "value": f"Price({current_price:.2f}) < Lower({lower_band:.2f})", "weight": 0.2})
        else:
            prediction_factors.append({"factor": "Bollinger Bands", "signal": "neutral", "value": f"Within bands", "weight": 0.1})
        
        # Price change momentum
        price_changes = hist['Close'].pct_change(5).iloc[-5:].mean() * 100  # 5-day average change
        if price_changes > 1:
            prediction_factors.append({"factor": "Price Momentum", "signal": "bullish", "value": f"{price_changes:.2f}%", "weight": 0.2})
        elif price_changes < -1:
            prediction_factors.append({"factor": "Price Momentum", "signal": "bearish", "value": f"{price_changes:.2f}%", "weight": 0.2})
        else:
            prediction_factors.append({"factor": "Price Momentum", "signal": "neutral", "value": f"{price_changes:.2f}%", "weight": 0.1})
        
        # Volume Analysis
        volume_change = hist['Volume'].pct_change(5).iloc[-5:].mean() * 100
        if volume_change > 20 and price_changes > 0:
            prediction_factors.append({"factor": "Volume Trend", "signal": "bullish", "value": f"{volume_change:.2f}%", "weight": 0.15})
        elif volume_change > 20 and price_changes < 0:
            prediction_factors.append({"factor": "Volume Trend", "signal": "bearish", "value": f"{volume_change:.2f}%", "weight": 0.15})
        else:
            prediction_factors.append({"factor": "Volume Trend", "signal": "neutral", "value": f"{volume_change:.2f}%", "weight": 0.05})
        
        # Simple Machine Learning Model
        # Prepare data for ML model
        ml_data = hist.copy()
        
        # Feature engineering
        ml_data['Price_SMA20_Ratio'] = ml_data['Close'] / ml_data['SMA20']
        ml_data['Price_SMA50_Ratio'] = ml_data['Close'] / ml_data['SMA50']
        ml_data['SMA20_SMA50_Ratio'] = ml_data['SMA20'] / ml_data['SMA50']
        ml_data['RSI_Scaled'] = ml_data['RSI'] / 100  # Scale RSI to 0-1
        ml_data['MACD_Signal_Diff'] = ml_data['MACD'] - ml_data['Signal']
        
        # Add more sophisticated features
        ml_data['Price_BB_Position'] = (ml_data['Close'] - ml_data['Lower Band']) / (ml_data['Upper Band'] - ml_data['Lower Band'])
        ml_data['Volume_Change'] = ml_data['Volume'].pct_change(5).rolling(window=5).mean()
        ml_data['Price_Volatility'] = ml_data['Close'].pct_change().rolling(window=10).std()
        
        # Create target: 1 if price went up in next 7 days, 0 if not
        ml_data['Target'] = ml_data['Close'].shift(-7) > ml_data['Close']
        ml_data = ml_data.dropna()
        
        if len(ml_data) > 30:  # Only use ML if we have enough data
            try:
                # Features and target
                features = ['Price_SMA20_Ratio', 'Price_SMA50_Ratio', 'SMA20_SMA50_Ratio', 
                           'RSI_Scaled', 'MACD_Signal_Diff', 'Price_BB_Position', 
                           'Volume_Change', 'Price_Volatility']
                X = ml_data[features].values
                y = ml_data['Target'].astype(int).values
                
                # Try more advanced model if enough data
                if len(ml_data) > 100:
                    from sklearn.ensemble import RandomForestClassifier
                    from sklearn.preprocessing import StandardScaler
                    
                    # Scale the features
                    scaler = StandardScaler()
                    X_scaled = scaler.fit_transform(X)
                    
                    # Split data (use most recent data for validation)
                    split_idx = int(len(X_scaled) * 0.8)
                    X_train, X_test = X_scaled[:split_idx], X_scaled[split_idx:]
                    y_train, y_test = y[:split_idx], y[split_idx:]
                    
                    # Train model
                    model = RandomForestClassifier(n_estimators=100, random_state=42)
                    model.fit(X_train, y_train)
                else:
                    # Use logistic regression for smaller datasets
                    from sklearn.linear_model import LogisticRegression
                    from sklearn.preprocessing import StandardScaler
                    
                    # Scale the features
                    scaler = StandardScaler()
                    X_scaled = scaler.fit_transform(X)
                    
                    # Split data (use most recent data for validation)
                    split_idx = int(len(X_scaled) * 0.8)
                    X_train, X_test = X_scaled[:split_idx], X_scaled[split_idx:]
                    y_train, y_test = y[:split_idx], y[split_idx:]
                    
                    # Train model
                    model = LogisticRegression(random_state=42)
                    model.fit(X_train, y_train)
                
                # Make prediction for current data
                current_features = np.array([[
                    ml_data['Price_SMA20_Ratio'].iloc[-1],
                    ml_data['Price_SMA50_Ratio'].iloc[-1],
                    ml_data['SMA20_SMA50_Ratio'].iloc[-1],
                    ml_data['RSI_Scaled'].iloc[-1],
                    ml_data['MACD_Signal_Diff'].iloc[-1],
                    ml_data['Price_BB_Position'].iloc[-1],
                    ml_data['Volume_Change'].iloc[-1],
                    ml_data['Price_Volatility'].iloc[-1]
                ]])
                
                current_features_scaled = scaler.transform(current_features)
                ml_prediction = model.predict(current_features_scaled)[0]
                ml_probability = model.predict_proba(current_features_scaled)[0][1]  # Probability of going up
                
                # Add ML prediction to factors
                ml_signal = "bullish" if ml_prediction == 1 else "bearish"
                prediction_factors.append({
                    "factor": "Machine Learning Model", 
                    "signal": ml_signal, 
                    "value": f"{ml_probability:.2f} probability", 
                    "weight": 0.35  # Give ML prediction higher weight
                })
                
                # Include sentiment analysis from news
                # This is a simplified approximation using technical indicators as proxy for sentiment
                sentiment_score = 0
                if rsi < 30:  # Oversold condition often indicates negative sentiment
                    sentiment_score = -0.5
                elif rsi > 70:  # Overbought condition often indicates positive sentiment
                    sentiment_score = 0.5
                
                # Adjust sentiment based on recent price momentum
                if price_changes > 3:  # Strong positive momentum
                    sentiment_score += 0.3
                elif price_changes < -3:  # Strong negative momentum
                    sentiment_score -= 0.3
                
                # Add sentiment factor
                sentiment_signal = "bullish" if sentiment_score > 0.2 else "bearish" if sentiment_score < -0.2 else "neutral"
                prediction_factors.append({
                    "factor": "Market Sentiment", 
                    "signal": sentiment_signal, 
                    "value": f"{sentiment_score:.2f} score", 
                    "weight": 0.25
                })
                
                # Generate future price projection for visualization
                future_prices = []
                last_price = current_price
                
                # Enhanced projection based on ML model confidence and sentiment
                base_daily_change = hist['Close'].pct_change().iloc[-14:].mean()
                
                # Weight the prediction more heavily based on ML confidence
                ml_weight = abs(ml_probability - 0.5) * 2  # 0 to 1 scale
                ml_adjustment = 0.008 * ml_weight if ml_prediction == 1 else -0.008 * ml_weight
                
                # Add sentiment influence
                sentiment_adjustment = sentiment_score * 0.002
                
                for i in range(7):  # Project 7 days into future
                    # Combine all factors for projection
                    projected_change = base_daily_change + ml_adjustment + sentiment_adjustment
                    
                    # Add some randomness that decreases over time for more realistic prediction
                    noise_factor = max(0.003 - (i * 0.0003), 0.001)
                    noise = np.random.normal(0, noise_factor)
                    
                    # Calculate next price
                    next_price = last_price * (1 + projected_change + noise)
                    future_prices.append(next_price)
                    last_price = next_price
                
            except Exception as e:
                print(f"Error in machine learning prediction: {e}")
                # If ML fails, don't add ML factor
                future_prices = []
                for i in range(7):
                    # Simple projection based on recent trend
                    noise = np.random.normal(0, 0.005)
                    future_prices.append(current_price * (1 + (i+1) * 0.002 * (1 if price_changes > 0 else -1) + noise))
        else:
            # If not enough data for ML, use simpler projection
            future_prices = []
            for i in range(7):
                # Simple projection based on recent trend
                noise = np.random.normal(0, 0.005)
                future_prices.append(current_price * (1 + (i+1) * 0.002 * (1 if price_changes > 0 else -1) + noise))
        
        # Calculate weighted prediction
        bullish_score = sum([factor["weight"] for factor in prediction_factors if factor["signal"] == "bullish"])
        bearish_score = sum([factor["weight"] for factor in prediction_factors if factor["signal"] == "bearish"])
        
        # Determine final prediction
        prediction = "up" if bullish_score > bearish_score else "down"
        confidence = max(bullish_score, bearish_score) / sum([factor["weight"] for factor in prediction_factors]) * 100
        
        # Get stock info for context
        try:
            stock_info = ticker.info
            company_name = stock_info.get('longName', symbol)
            sector = stock_info.get('sector', 'Unknown Sector')
            industry = stock_info.get('industry', 'Unknown Industry')
        except Exception as e:
            print(f"Error getting stock info: {e}")
            company_name = symbol
            sector = "Unknown Sector"
            industry = "Unknown Industry"
        
        # Format analysis factors for AI prompt
        factors_text = "\n".join([f"- {factor['factor']}: {factor['signal'].upper()} ({factor['value']})" for factor in prediction_factors])
        
        # Generate AI explanation using Groq
        try:
            client = groq.Groq(api_key=os.environ.get('GROQ_API_KEY'))
            
            prompt = f"""
            You are a financial analyst providing an explanation for a stock prediction.
            
            Stock: {company_name} ({symbol})
            Sector: {sector}
            Industry: {industry}
            Current Price: ${current_price:.2f}
            
            Technical Analysis Factors:
            {factors_text}
            
            Overall Prediction: Stock will likely go {prediction.upper()} with {confidence:.1f}% confidence.
            
            Based on this information, provide a detailed but concise explanation of why {symbol} is predicted to go {prediction}. 
            Focus on the most important technical indicators and their implications. 
            Explain in clear terms that a retail investor would understand.
            
            Structure your explanation in these sections:
            1. Summary (2-3 sentences)
            2. Key Technical Indicators (bullet points explaining the most important signals)
            3. Market Context (1-2 sentences about market conditions)
            4. Conclusion (1-2 sentences with outlook)
            
            Keep your total response under 400 words and focus on being educational and insightful.
            """
            
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a financial analyst providing stock predictions."},
                    {"role": "user", "content": prompt}
                ],
                model="llama3-70b-8192",
                temperature=0.5,
                max_tokens=600,
                top_p=1,
                stream=False
            )
            
            explanation = chat_completion.choices[0].message.content
        except Exception as e:
            print(f"Error generating AI explanation: {e}")
            explanation = f"Based on technical analysis, {symbol} is predicted to go {prediction} with {confidence:.1f}% confidence. Key factors include RSI, moving averages, MACD, and recent price momentum."
        
        # Format dates for future projection
        last_date = datetime.strptime(dates[-1], '%Y-%m-%d')
        future_dates = [(last_date + timedelta(days=i+1)).strftime('%Y-%m-%d') for i in range(7)]
        
        # Create more accurate predicted price visualization
        # First, create an array that properly shows null values for historical dates
        # and predicted values only for future dates
        all_predicted_prices = [None] * len(dates)
        
        # Connect the last actual price with first predicted price for visual continuity
        # This ensures there's no gap between historical and predicted data
        all_predicted_prices[-1] = current_price  # Connect the last historical point
        all_predicted_prices.extend(future_prices)  # Add the future predictions
        
        # Combine historical and future data for visualization
        visualization_data = {
            "dates": dates + future_dates,
            "prices": historical_prices + [None] * 7,  # Historical prices with None for future dates
            "predicted": all_predicted_prices  # Now includes connecting point for better visualization
        }
        
        result = {
            "symbol": symbol,
            "company_name": company_name,
            "current_price": current_price,
            "prediction": prediction,
            "confidence": round(confidence, 1),
            "explanation": explanation,
            "analysis_factors": prediction_factors,
            "visualization_data": visualization_data,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in stock prediction: {e}")
        return jsonify({
            "error": f"Failed to analyze {symbol}: {str(e)}",
            "symbol": symbol
        })

# Check database tables and initialize if needed
def check_db_tables():
    try:
        conn = get_db_connection()
        # Try to query the users table to see if it exists
        conn.execute('SELECT 1 FROM users LIMIT 1')
        conn.close()
        print("Database tables already exist")
        return True
    except sqlite3.OperationalError:
        # Table doesn't exist, initialize DB
        print("Database tables not found. Initializing database...")
        init_db()
        print("Database initialized successfully")
        return False

# Initialize database at startup
with app.app_context():
    check_db_tables()

if __name__ == '__main__':
    # Check if database exists, if not initialize it
    if not os.path.exists(app.config['DATABASE']):
        init_db()
    else:
        # Even if file exists, check if tables are present
        check_db_tables()
    
    app.run(debug=False)
