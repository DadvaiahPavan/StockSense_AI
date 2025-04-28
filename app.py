import os
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import json
from datetime import datetime
import pandas as pd
import yfinance as yf
from dotenv import load_dotenv

# Import services
from services.stock_service import get_stock_data, get_stock_info, search_stocks, get_market_indices, get_watchlist_prices, get_portfolio_data
from services.yahoo_scraper import get_yahoo_market_stocks
from services.ai_service import generate_investment_thesis, analyze_stock_movement, chat_with_ai
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
    # Get market indices data using our improved service
    indices_data = get_market_indices()
    
    # Get user's watchlist
    conn = get_db_connection()
    watchlist_items = conn.execute('SELECT * FROM watchlist WHERE user_id = ?', (current_user.id,)).fetchall()
    conn.close()
    
    # Extract symbols from watchlist
    watchlist_symbols = [item['symbol'] for item in watchlist_items]
    
    # Get real-time watchlist data using our improved service
    if watchlist_symbols:
        watchlist_prices = get_watchlist_prices(watchlist_symbols)
        watchlist_data = []
        for symbol in watchlist_symbols:
            if symbol in watchlist_prices:
                watchlist_data.append(watchlist_prices[symbol])
    else:
        watchlist_data = []
    
    # Get Yahoo Finance stock data for different categories
    most_active_stocks = get_yahoo_market_stocks('most-active')
    trending_stocks = get_yahoo_market_stocks('trending')
    gainers_stocks = get_yahoo_market_stocks('gainers')
    losers_stocks = get_yahoo_market_stocks('losers')
    week52_gainers_stocks = get_yahoo_market_stocks('52-week-gainers')
    week52_losers_stocks = get_yahoo_market_stocks('52-week-losers')
    
    # Get latest market news using our improved scraper service
    news = get_market_news(query='MARKET', limit=5)
    
    return render_template('dashboard.html', 
                          indices=indices_data, 
                          watchlist=watchlist_data,
                          most_active=most_active_stocks,
                          trending=trending_stocks,
                          gainers=gainers_stocks,
                          losers=losers_stocks,
                          week52_gainers=week52_gainers_stocks,
                          week52_losers=week52_losers_stocks,
                          news=news)

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
    
    conn = get_db_connection()
    conn.execute('DELETE FROM watchlist WHERE user_id = ? AND symbol = ?', 
                (current_user.id, symbol))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/strategy-builder')
@login_required
def strategy_builder():
    predefined_strategies = get_predefined_strategies()
    return render_template('strategy_builder.html', strategies=predefined_strategies)

@app.route('/api/strategy/backtest', methods=['POST'])
@login_required
def api_backtest_strategy():
    data = request.json
    symbol = data.get('symbol')
    strategy_type = data.get('strategy_type')
    parameters = data.get('parameters', {})
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    results = backtest_strategy(symbol, strategy_type, parameters, start_date, end_date)
    return jsonify(results)

@app.route('/stock-analysis/<symbol>')
@login_required
def stock_analysis(symbol):
    # Get stock information
    stock_info = get_stock_info(symbol)
    
    # Get AI analysis
    analysis = analyze_stock_movement(symbol)
    
    return render_template('stock_analysis.html',
                          symbol=symbol,
                          stock_info=stock_info,
                          analysis=analysis)

@app.route('/investment-thesis/<symbol>')
@login_required
def investment_thesis(symbol):
    # Get stock information
    stock_info = get_stock_info(symbol)
    
    # Get social sentiment
    sentiment = get_social_sentiment(symbol)
    
    # Generate thesis using AI
    thesis = generate_investment_thesis(symbol, stock_info, sentiment)
    
    return render_template('investment_thesis.html',
                          symbol=symbol,
                          stock_info=stock_info,
                          thesis=thesis,
                          sentiment=sentiment)

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

if __name__ == '__main__':
    # Check if database exists, if not initialize it
    if not os.path.exists(app.config['DATABASE']):
        init_db()
    
    app.run(debug=True)
