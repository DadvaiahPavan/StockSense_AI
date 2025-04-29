import os
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import groq

# No longer need OpenAI
# openai.api_key = os.environ.get('OPENAI_API_KEY')

def analyze_stock_movement(symbol):
    """
    Analyze a stock's recent price movements and provide AI insights
    """
    try:
        # Get historical data
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="6mo")
        
        if hist.empty:
            return {
                "sentiment": "neutral",
                "confidence": 0.5,
                "summary": f"No data available for {symbol}. Unable to perform analysis.",
                "key_factors": ["No data available"],
                "prediction": "Insufficient data for prediction"
            }
        
        # Calculate some basic technical indicators
        hist['SMA20'] = hist['Close'].rolling(window=20).mean()
        hist['SMA50'] = hist['Close'].rolling(window=50).mean()
        hist['RSI'] = calculate_rsi(hist['Close'])
        
        # Get recent price and calculate changes
        current_price = hist['Close'].iloc[-1]
        price_change_1d = (current_price / hist['Close'].iloc[-2] - 1) * 100 if len(hist) > 1 else 0
        price_change_1w = (current_price / hist['Close'].iloc[-5] - 1) * 100 if len(hist) > 5 else 0
        price_change_1m = (current_price / hist['Close'].iloc[-20] - 1) * 100 if len(hist) > 20 else 0
        
        # Determine trend direction
        trend = "bullish" if hist['SMA20'].iloc[-1] > hist['SMA50'].iloc[-1] else "bearish"
        
        # Simple sentiment based on recent performance and RSI
        rsi = hist['RSI'].iloc[-1]
        
        if rsi > 70:
            sentiment = "overbought"
            confidence = min(0.5 + (rsi - 70) / 60, 0.9)
        elif rsi < 30:
            sentiment = "oversold"
            confidence = min(0.5 + (30 - rsi) / 60, 0.9)
        elif price_change_1m > 10:
            sentiment = "bullish"
            confidence = min(0.5 + price_change_1m / 20, 0.9)
        elif price_change_1m < -10:
            sentiment = "bearish"
            confidence = min(0.5 + abs(price_change_1m) / 20, 0.9)
        else:
            sentiment = "neutral"
            confidence = 0.5
        
        # Format the output
        analysis = {
            "sentiment": sentiment,
            "confidence": round(confidence, 2),
            "summary": f"{symbol} shows a {sentiment} trend with {round(confidence*100)}% confidence. The stock is in a {trend} pattern.",
            "key_factors": [
                f"RSI at {round(rsi, 2)} indicates {'overbought' if rsi > 70 else 'oversold' if rsi < 30 else 'neutral'} conditions",
                f"Price change (1 day): {round(price_change_1d, 2)}%",
                f"Price change (1 week): {round(price_change_1w, 2)}%",
                f"Price change (1 month): {round(price_change_1m, 2)}%",
                f"20-day SMA is {'above' if hist['SMA20'].iloc[-1] > hist['SMA50'].iloc[-1] else 'below'} 50-day SMA"
            ],
            "prediction": "Likely to continue " + trend + " pattern in the short term"
        }
        
        return analysis
    
    except Exception as e:
        print(f"Error analyzing stock movement: {e}")
        return {
            "sentiment": "neutral",
            "confidence": 0.5,
            "summary": f"Error analyzing {symbol}. Please try again later.",
            "key_factors": ["Analysis error"],
            "prediction": "Unable to make prediction due to error"
        }

def chat_with_ai(message):
    """
    Send a message to Groq API (Llama3-70b-8192) and get a response
    
    Args:
        message: User's message
    
    Returns:
        Llama3 model response via Groq API
    """
    try:
        # Initialize Groq client with API key
        client = groq.Groq(api_key=os.environ.get('GROQ_API_KEY'))
        
        # Call Groq API with Llama3-70b-8192 model
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": "You are a financial advisor bot for StockSense AI. You help users with stock market questions, investment advice, and general financial knowledge. Keep responses concise but informative."},
                {"role": "user", "content": message}
            ],
            temperature=0.5,
            max_tokens=500,
            top_p=1,
            stream=False
        )
        
        # Extract the message from the response
        return response.choices[0].message.content
    
    except Exception as e:
        print(f"Error in chat_with_ai: {e}")
        return "I apologize, but I'm having trouble connecting to my knowledge base right now. Please try again later."

def calculate_rsi(prices, period=14):
    """Calculate Relative Strength Index"""
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed>=0].sum()/period
    down = -seed[seed<0].sum()/period
    rs = up/down
    rsi = np.zeros_like(prices)
    rsi[:period] = 100. - 100./(1.+rs)

    for i in range(period, len(prices)):
        delta = deltas[i-1]
        if delta > 0:
            upval = delta
            downval = 0.
        else:
            upval = 0.
            downval = -delta
            
        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period
        
        rs = up/down if down != 0 else 0
        rsi[i] = 100. - 100./(1.+rs)
        
    return rsi
