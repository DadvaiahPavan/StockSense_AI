import os
import sqlite3
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

# Database initialization
def init_db():
    # Check if database already exists
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stocksage.db')
    
    if os.path.exists(db_path):
        print(f"Database already exists at {db_path}")
        return
    
    print(f"Creating new database at {db_path}")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Create tables
    with open('schema.sql') as f:
        conn.executescript(f.read())
    
    # Add sample data
    # Create demo user
    password_hash = generate_password_hash('password123')
    conn.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                ('Demo User', 'demo@example.com', password_hash))
    
    # Add sample watchlist items
    sample_stocks = [
        (1, 'AAPL', 'Apple Inc.'),
        (1, 'MSFT', 'Microsoft Corporation'),
        (1, 'GOOGL', 'Alphabet Inc.'),
        (1, 'AMZN', 'Amazon.com, Inc.'),
        (1, 'TSLA', 'Tesla, Inc.'),
        (1, 'RELIANCE.NS', 'Reliance Industries Limited')
    ]
    
    conn.executemany('INSERT INTO watchlist (user_id, symbol, name) VALUES (?, ?, ?)', sample_stocks)
    
    # Add sample portfolio items
    today = datetime.now()
    sample_portfolio = [
        (1, 'AAPL', 'Apple Inc.', 10, 150.75, (today - timedelta(days=90)).strftime('%Y-%m-%d')),
        (1, 'MSFT', 'Microsoft Corporation', 5, 280.50, (today - timedelta(days=60)).strftime('%Y-%m-%d')),
        (1, 'GOOGL', 'Alphabet Inc.', 2, 2500.25, (today - timedelta(days=30)).strftime('%Y-%m-%d')),
        (1, 'AMZN', 'Amazon.com, Inc.', 3, 3200.10, (today - timedelta(days=45)).strftime('%Y-%m-%d')),
        (1, 'RELIANCE.NS', 'Reliance Industries Limited', 20, 2100.50, (today - timedelta(days=75)).strftime('%Y-%m-%d'))
    ]
    
    conn.executemany('INSERT INTO portfolio (user_id, symbol, name, shares, avg_price, purchase_date) VALUES (?, ?, ?, ?, ?, ?)', sample_portfolio)
    
    # Add sample saved strategies
    sample_strategies = [
        (1, 'Golden Cross Strategy', 'sma_crossover', '{"short_window": 20, "long_window": 50}'),
        (1, 'RSI Oversold Strategy', 'rsi', '{"rsi_period": 14, "oversold": 30, "overbought": 70}')
    ]
    
    conn.executemany('INSERT INTO strategies (user_id, name, strategy_type, parameters) VALUES (?, ?, ?, ?)', sample_strategies)
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("Database initialized with sample data")

if __name__ == '__main__':
    init_db()
