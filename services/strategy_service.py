import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import json

def get_predefined_strategies():
    """
    Get a list of predefined trading strategies
    
    Returns:
        List of strategy dictionaries with name, description, and parameters
    """
    strategies = [
        {
            'id': 'sma_crossover',
            'name': 'SMA Crossover',
            'description': 'Simple Moving Average crossover strategy. Buy when short-term SMA crosses above long-term SMA, sell when it crosses below.',
            'parameters': {
                'short_window': {'type': 'int', 'default': 20, 'min': 5, 'max': 50, 'description': 'Short-term SMA period'},
                'long_window': {'type': 'int', 'default': 50, 'min': 20, 'max': 200, 'description': 'Long-term SMA period'}
            }
        },
        {
            'id': 'rsi',
            'name': 'RSI Strategy',
            'description': 'Relative Strength Index strategy. Buy when RSI is below oversold level, sell when RSI is above overbought level.',
            'parameters': {
                'rsi_period': {'type': 'int', 'default': 14, 'min': 7, 'max': 30, 'description': 'RSI calculation period'},
                'oversold': {'type': 'int', 'default': 30, 'min': 10, 'max': 40, 'description': 'Oversold level'},
                'overbought': {'type': 'int', 'default': 70, 'min': 60, 'max': 90, 'description': 'Overbought level'}
            }
        },
        {
            'id': 'macd',
            'name': 'MACD Strategy',
            'description': 'Moving Average Convergence Divergence strategy. Buy when MACD line crosses above signal line, sell when it crosses below.',
            'parameters': {
                'fast_period': {'type': 'int', 'default': 12, 'min': 8, 'max': 20, 'description': 'Fast EMA period'},
                'slow_period': {'type': 'int', 'default': 26, 'min': 20, 'max': 40, 'description': 'Slow EMA period'},
                'signal_period': {'type': 'int', 'default': 9, 'min': 5, 'max': 15, 'description': 'Signal line period'}
            }
        },
        {
            'id': 'bollinger',
            'name': 'Bollinger Bands Strategy',
            'description': 'Bollinger Bands strategy. Buy when price touches lower band, sell when price touches upper band.',
            'parameters': {
                'window': {'type': 'int', 'default': 20, 'min': 10, 'max': 50, 'description': 'Window period'},
                'num_std': {'type': 'float', 'default': 2.0, 'min': 1.0, 'max': 3.0, 'description': 'Number of standard deviations'}
            }
        },
        {
            'id': 'custom',
            'name': 'Custom Strategy',
            'description': 'Create your own custom strategy using a combination of technical indicators.',
            'parameters': {
                'code': {'type': 'text', 'default': '', 'description': 'Custom strategy code'}
            }
        }
    ]
    
    return strategies

def calculate_sma(data, window):
    """Calculate Simple Moving Average"""
    return data['Close'].rolling(window=window).mean()

def calculate_rsi(data, window=14):
    """Calculate Relative Strength Index"""
    delta = data['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=window).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=window).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def calculate_macd(data, fast_period=12, slow_period=26, signal_period=9):
    """Calculate Moving Average Convergence Divergence"""
    fast_ema = data['Close'].ewm(span=fast_period, adjust=False).mean()
    slow_ema = data['Close'].ewm(span=slow_period, adjust=False).mean()
    
    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    
    return macd_line, signal_line

def calculate_bollinger_bands(data, window=20, num_std=2):
    """Calculate Bollinger Bands"""
    sma = data['Close'].rolling(window=window).mean()
    std = data['Close'].rolling(window=window).std()
    
    upper_band = sma + (std * num_std)
    lower_band = sma - (std * num_std)
    
    return upper_band, lower_band

def _sanitize_json_data(data):
    """
    Sanitize data for JSON serialization by handling NaN values
    """
    if isinstance(data, dict):
        return {k: _sanitize_json_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_sanitize_json_data(item) for item in data]
    elif isinstance(data, (np.float64, np.float32, float)) and np.isnan(data):
        return None
    else:
        return data

def backtest_strategy(symbol, strategy_type, parameters, start_date, end_date):
    """
    Backtest a trading strategy
    
    Args:
        symbol: Stock ticker symbol
        strategy_type: Type of strategy to backtest
        parameters: Dictionary of strategy parameters
        start_date: Start date for backtesting
        end_date: End date for backtesting
    
    Returns:
        Dictionary with backtest results
    """
    try:
        # Validate symbol
        if not symbol or len(symbol.strip()) == 0:
            return {'error': 'Invalid stock symbol'}
            
        # Clean the symbol
        symbol = symbol.strip().upper()
        
        # Get historical data
        data = pd.DataFrame()
        error_message = None
        
        # Try different symbol formats
        symbol_variations = [symbol]
        
        # For non-suffixed symbols, try with common suffixes
        if not any(symbol.endswith(suffix) for suffix in ['.NS', '.BO', '.BSE', '.N', '.O']):
            symbol_variations.extend([f"{symbol}.NS", f"{symbol}.BO"])
        
        # For suffixed symbols, also try the base symbol
        elif any(symbol.endswith(suffix) for suffix in ['.NS', '.BO', '.BSE', '.N', '.O']):
            base_symbol = symbol.split('.')[0]
            if base_symbol not in symbol_variations:
                symbol_variations.append(base_symbol)
        
        # Try each symbol variation
        for sym in symbol_variations:
            try:
                print(f"Trying symbol: {sym}")
                ticker = yf.Ticker(sym)
                temp_data = ticker.history(start=start_date, end=end_date)
                
                if not temp_data.empty:
                    data = temp_data
                    symbol = sym  # Update to the working symbol
                    print(f"Successfully fetched data for {symbol}")
                    break
            except Exception as e:
                error_message = str(e)
                print(f"Error fetching data for {sym}: {e}")
        
        if data.empty:
            return {'error': f'No data available for this symbol ({symbol}) and date range. {error_message if error_message else ""}'}
        
        # Initialize signals DataFrame
        signals = pd.DataFrame(index=data.index)
        signals['price'] = data['Close']
        signals['signal'] = 0  # 0: no position, 1: long position
        signals['position'] = 0
        
        # Apply strategy
        if strategy_type == 'sma_crossover':
            short_window = parameters.get('short_window', 20)
            long_window = parameters.get('long_window', 50)
            
            # Calculate moving averages
            signals['short_mavg'] = calculate_sma(data, short_window)
            signals['long_mavg'] = calculate_sma(data, long_window)
            
            # Generate signals - using loc to avoid ChainedAssignment warning
            signals.loc[signals.index[short_window:], 'signal'] = np.where(
                signals['short_mavg'][short_window:] > signals['long_mavg'][short_window:], 1, 0
            )
            
            # Add indicator data for visualization
            indicator_data = {
                'short_mavg': signals['short_mavg'].tolist(),
                'long_mavg': signals['long_mavg'].tolist()
            }
        
        elif strategy_type == 'rsi':
            rsi_period = parameters.get('rsi_period', 14)
            oversold = parameters.get('oversold', 30)
            overbought = parameters.get('overbought', 70)
            
            # Calculate RSI
            signals['rsi'] = calculate_rsi(data, rsi_period)
            
            # Generate signals
            signals['signal'] = 0
            signals['signal'] = np.where(signals['rsi'] < oversold, 1, signals['signal'])
            signals['signal'] = np.where(signals['rsi'] > overbought, 0, signals['signal'])
            
            # Add indicator data for visualization
            indicator_data = {
                'rsi': signals['rsi'].tolist(),
                'oversold': [oversold] * len(signals),
                'overbought': [overbought] * len(signals)
            }
        
        elif strategy_type == 'macd':
            fast_period = parameters.get('fast_period', 12)
            slow_period = parameters.get('slow_period', 26)
            signal_period = parameters.get('signal_period', 9)
            
            # Calculate MACD
            macd_line, signal_line = calculate_macd(data, fast_period, slow_period, signal_period)
            signals['macd'] = macd_line
            signals['signal_line'] = signal_line
            
            # Generate signals
            signals.loc[signals.index[signal_period:], 'signal'] = np.where(
                signals['macd'][signal_period:] > signals['signal_line'][signal_period:], 1, 
                np.where(signals['macd'][signal_period:] < signals['signal_line'][signal_period:], -1, 0)
            )
            
            # Add indicator data for visualization
            indicator_data = {
                'macd': signals['macd'].tolist(),
                'signal_line': signals['signal_line'].tolist(),
                'histogram': (signals['macd'] - signals['signal_line']).tolist()
            }
        
        elif strategy_type == 'bollinger':
            window = parameters.get('window', 20)
            num_std = parameters.get('num_std', 2.0)
            
            # Calculate Bollinger Bands
            upper_band, lower_band = calculate_bollinger_bands(data, window, num_std)
            signals['upper_band'] = upper_band
            signals['lower_band'] = lower_band
            signals['middle_band'] = calculate_sma(data, window)
            
            # Generate signals
            signals['signal'] = 0
            signals['signal'] = np.where(signals['price'] < signals['lower_band'], 1, signals['signal'])
            signals['signal'] = np.where(signals['price'] > signals['upper_band'], -1, signals['signal'])
            
            # Add indicator data for visualization
            indicator_data = {
                'upper_band': signals['upper_band'].tolist(),
                'middle_band': signals['middle_band'].tolist(),
                'lower_band': signals['lower_band'].tolist()
            }
        
        else:
            return {'error': f'Unknown strategy type: {strategy_type}'}
        
        # Calculate positions (entry and exit points)
        signals['position'] = signals['signal'].diff().fillna(0)
        
        # Calculate returns
        signals['returns'] = data['Close'].pct_change()
        signals['strategy_returns'] = signals['returns'] * signals['signal'].shift(1)
        
        # Calculate cumulative returns
        signals['cumulative_returns'] = (1 + signals['returns']).cumprod()
        signals['cumulative_strategy_returns'] = (1 + signals['strategy_returns']).cumprod()
        
        # Find trade entry and exit points
        buy_signals = signals[signals['position'] == 1]
        sell_signals = signals[signals['position'] == -1]
        
        trades = []
        for i in range(min(len(buy_signals), len(sell_signals))):
            buy_date = buy_signals.index[i].strftime('%Y-%m-%d')
            buy_price = buy_signals['price'].iloc[i]
            
            sell_date = sell_signals.index[i].strftime('%Y-%m-%d')
            sell_price = sell_signals['price'].iloc[i]
            
            profit = sell_price - buy_price
            profit_percent = (profit / buy_price) * 100
            
            trades.append({
                'entry_date': buy_date,
                'entry_price': float(buy_price),
                'exit_date': sell_date,
                'exit_price': float(sell_price),
                'profit': float(profit),
                'profit_percent': float(profit_percent)
            })
        
        # Calculate performance metrics
        total_trades = len(trades)
        winning_trades = sum(1 for trade in trades if trade['profit'] > 0)
        losing_trades = total_trades - winning_trades
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        total_return = signals['cumulative_strategy_returns'].iloc[-1] - 1 if not signals['cumulative_strategy_returns'].empty else 0
        buy_hold_return = signals['cumulative_returns'].iloc[-1] - 1 if not signals['cumulative_returns'].empty else 0
        
        # Calculate drawdown
        drawdown = 1 - signals['cumulative_strategy_returns'] / signals['cumulative_strategy_returns'].cummax()
        max_drawdown = drawdown.max()
        
        # Prepare result
        result = {
            'symbol': symbol,
            'strategy': strategy_type,
            'parameters': parameters,
            'start_date': start_date,
            'end_date': end_date,
            'trades': trades,
            'metrics': {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': float(win_rate),
                'total_return': float(total_return),
                'buy_hold_return': float(buy_hold_return),
                'max_drawdown': float(max_drawdown)
            },
            'chart_data': {
                'dates': [date.strftime('%Y-%m-%d') for date in signals.index],
                'prices': [float(x) if not np.isnan(x) else None for x in signals['price'].tolist()],
                'cumulative_returns': [float(x) if not np.isnan(x) else None for x in signals['cumulative_returns'].tolist()],
                'cumulative_strategy_returns': [float(x) if not np.isnan(x) else None for x in signals['cumulative_strategy_returns'].tolist()],
                'indicators': _sanitize_json_data(indicator_data)
            }
        }
        
        return result
    
    except Exception as e:
        print(f"Error backtesting strategy for {symbol}: {e}")
        return {'error': str(e)}
