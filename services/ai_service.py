import os
import groq
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

# Load environment variables
load_dotenv()

# Initialize Groq client
client = groq.Groq(api_key=os.environ.get('GROQ_API_KEY', 'your-groq-api-key'))
MODEL = "llama3-70b-8192"  # Can be changed to mixtral-8x7b-32768 or other models

def chat_with_ai(message, context=None):
    """
    Send a message to the Groq API and get a response
    
    Args:
        message: User message
        context: Optional context information
    
    Returns:
        AI response as a string
    """
    try:
        # Create system prompt with financial expertise
        system_prompt = """You are StockSense AI, an expert AI financial advisor specializing in stock market analysis.
You provide clear, concise, and accurate information about stocks, market trends, and investment strategies.
Always base your answers on factual information and financial principles.
If you don't know something, admit it rather than making up information.
Keep responses focused on financial topics and avoid political opinions.
"""
        
        # Add market context if available
        if context:
            system_prompt += f"\nCurrent market context: {context}"
        
        # Call Groq API
        chat_completion = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            temperature=0.2,
            max_tokens=1024
        )
        
        return chat_completion.choices[0].message.content
    
    except Exception as e:
        print(f"Error calling Groq API: {e}")
        return f"I'm sorry, I encountered an error: {str(e)}. Please try again later."

def analyze_stock_movement(symbol):
    """
    Generate AI analysis of stock movement and predictions
    
    Args:
        symbol: Stock ticker symbol
    
    Returns:
        Dictionary with AI analysis results
    """
    try:
        # Get historical data
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period='1y')
        
        if hist.empty:
            return {'error': 'No data available for this symbol'}
        
        # Calculate some basic metrics
        current_price = hist['Close'].iloc[-1]
        price_30d_ago = hist['Close'].iloc[-30] if len(hist) >= 30 else hist['Close'].iloc[0]
        price_90d_ago = hist['Close'].iloc[-90] if len(hist) >= 90 else hist['Close'].iloc[0]
        
        change_30d = ((current_price - price_30d_ago) / price_30d_ago) * 100
        change_90d = ((current_price - price_90d_ago) / price_90d_ago) * 100
        
        # Calculate volatility (standard deviation of returns)
        returns = hist['Close'].pct_change().dropna()
        volatility = returns.std() * (252 ** 0.5)  # Annualized volatility
        
        # Prepare context for AI
        info = ticker.info
        company_name = info.get('shortName', info.get('longName', symbol))
        sector = info.get('sector', 'Unknown')
        industry = info.get('industry', 'Unknown')
        
        # Recent price data
        recent_prices = hist['Close'].tail(30).tolist()
        recent_volumes = hist['Volume'].tail(30).tolist()
        
        # Create prompt for Groq
        prompt = f"""Analyze the stock movement and provide a prediction for {company_name} ({symbol}) based on the following data:

Company Information:
- Name: {company_name}
- Symbol: {symbol}
- Sector: {sector}
- Industry: {industry}
- Current Price: ${current_price:.2f}

Performance:
- 30-day change: {change_30d:.2f}%
- 90-day change: {change_90d:.2f}%
- Volatility (annualized): {volatility:.2f}

Recent price trend (last 30 days): {recent_prices}
Recent volume trend (last 30 days): {recent_volumes}

Provide the following analysis:
1. A brief summary of recent price movement
2. Key factors influencing the stock
3. Technical indicators assessment
4. Price prediction for 7 days and 30 days
5. Risk assessment (Low, Medium, High)
6. Overall sentiment (Bullish, Neutral, Bearish)

Format your response as JSON with the following structure:
{{
  "summary": "Brief summary of recent movement",
  "key_factors": ["Factor 1", "Factor 2", "Factor 3"],
  "technical_analysis": "Technical indicators assessment",
  "prediction_7d": {{
    "direction": "up/down/sideways",
    "confidence": "percentage",
    "target_price": "price"
  }},
  "prediction_30d": {{
    "direction": "up/down/sideways",
    "confidence": "percentage",
    "target_price": "price"
  }},
  "risk_assessment": "Low/Medium/High",
  "sentiment": "Bullish/Neutral/Bearish",
  "reasoning": "Detailed reasoning for the prediction"
}}
"""
        
        # Call Groq API
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a professional stock market analyst with expertise in technical and fundamental analysis."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=1024
        )
        
        # Parse the response
        analysis_text = response.choices[0].message.content
        
        # Extract JSON from the response
        try:
            # Find JSON in the response (it might be wrapped in markdown code blocks)
            if "```json" in analysis_text:
                json_str = analysis_text.split("```json")[1].split("```")[0].strip()
            elif "```" in analysis_text:
                json_str = analysis_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = analysis_text
            
            analysis = json.loads(json_str)
            
            # Add timestamp
            analysis['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            analysis['current_price'] = current_price
            
            return analysis
        
        except json.JSONDecodeError:
            # If JSON parsing fails, return the raw text with default prediction values
            return {
                'error': 'Failed to parse AI response as JSON',
                'raw_analysis': analysis_text,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'current_price': current_price,
                # Add default prediction values to prevent template errors
                'prediction_7d': {
                    'direction': 'sideways',
                    'confidence': 'N/A',
                    'target_price': current_price
                },
                'prediction_30d': {
                    'direction': 'sideways',
                    'confidence': 'N/A',
                    'target_price': current_price
                },
                'summary': 'Unable to generate analysis at this time.',
                'key_factors': ['Data unavailable'],
                'technical_analysis': 'Analysis unavailable',
                'risk_assessment': 'Medium',
                'sentiment': 'Neutral',
                'reasoning': 'AI analysis could not be generated properly.'
            }
    
    except Exception as e:
        print(f"Error analyzing stock movement for {symbol}: {e}")
        return {'error': str(e)}

def generate_investment_thesis(symbol, stock_info, sentiment_data):
    """
    Generate a comprehensive investment thesis for a stock
    
    Args:
        symbol: Stock ticker symbol
        stock_info: Dictionary with stock information
        sentiment_data: Dictionary with sentiment analysis
    
    Returns:
        Dictionary with investment thesis sections
    """
    try:
        # Get additional financial data
        ticker = yf.Ticker(symbol)
        
        # Get financial statements if available
        income_stmt = ticker.income_stmt
        balance_sheet = ticker.balance_sheet
        cash_flow = ticker.cashflow
        
        # Extract key financial metrics
        financial_metrics = {}
        
        if not income_stmt.empty:
            financial_metrics['revenue'] = income_stmt.loc['Total Revenue'].iloc[0] if 'Total Revenue' in income_stmt.index else None
            financial_metrics['net_income'] = income_stmt.loc['Net Income'].iloc[0] if 'Net Income' in income_stmt.index else None
            financial_metrics['gross_margin'] = (income_stmt.loc['Gross Profit'].iloc[0] / income_stmt.loc['Total Revenue'].iloc[0]) if 'Gross Profit' in income_stmt.index and 'Total Revenue' in income_stmt.index else None
        
        if not balance_sheet.empty:
            financial_metrics['total_assets'] = balance_sheet.loc['Total Assets'].iloc[0] if 'Total Assets' in balance_sheet.index else None
            financial_metrics['total_debt'] = balance_sheet.loc['Total Debt'].iloc[0] if 'Total Debt' in balance_sheet.index else None
        
        if not cash_flow.empty:
            financial_metrics['operating_cash_flow'] = cash_flow.loc['Operating Cash Flow'].iloc[0] if 'Operating Cash Flow' in cash_flow.index else None
            financial_metrics['free_cash_flow'] = cash_flow.loc['Free Cash Flow'].iloc[0] if 'Free Cash Flow' in cash_flow.index else None
        
        # Create prompt for Groq
        company_name = stock_info.get('name', symbol)
        
        prompt = f"""Generate a comprehensive investment thesis for {company_name} ({symbol}) based on the following information:

Company Information:
- Name: {company_name}
- Symbol: {symbol}
- Sector: {stock_info.get('sector', 'N/A')}
- Industry: {stock_info.get('industry', 'N/A')}
- Current Price: ${stock_info.get('price', 'N/A')}
- Market Cap: ${stock_info.get('market_cap', 'N/A')}
- P/E Ratio: {stock_info.get('pe_ratio', 'N/A')}
- EPS: ${stock_info.get('eps', 'N/A')}
- 52-Week Range: ${stock_info.get('fifty_two_week_low', 'N/A')} - ${stock_info.get('fifty_two_week_high', 'N/A')}

Financial Metrics:
- Revenue: ${financial_metrics.get('revenue', 'N/A')}
- Net Income: ${financial_metrics.get('net_income', 'N/A')}
- Gross Margin: {financial_metrics.get('gross_margin', 'N/A')}
- Total Assets: ${financial_metrics.get('total_assets', 'N/A')}
- Total Debt: ${financial_metrics.get('total_debt', 'N/A')}
- Operating Cash Flow: ${financial_metrics.get('operating_cash_flow', 'N/A')}
- Free Cash Flow: ${financial_metrics.get('free_cash_flow', 'N/A')}

Market Sentiment:
- News Sentiment: {sentiment_data.get('news_sentiment', 'N/A')}
- Social Media Sentiment: {sentiment_data.get('social_sentiment', 'N/A')}
- Analyst Recommendations: {sentiment_data.get('analyst_recommendations', 'N/A')}

Company Description:
{stock_info.get('description', 'No description available')}

Generate a detailed investment thesis with the following sections:
1. Executive Summary
2. Business Overview
3. Industry Analysis
4. Financial Analysis
5. Competitive Positioning
6. Growth Catalysts
7. Risk Factors
8. Valuation Analysis
9. Investment Recommendation (Buy/Hold/Sell)

Format your response as JSON with the following structure:
{{
  "executive_summary": "Brief summary of the investment thesis",
  "business_overview": "Overview of the company's business model",
  "industry_analysis": "Analysis of the industry trends and outlook",
  "financial_analysis": "Analysis of the company's financial performance",
  "competitive_positioning": "Analysis of the company's competitive advantages",
  "growth_catalysts": ["Catalyst 1", "Catalyst 2", "Catalyst 3"],
  "risk_factors": ["Risk 1", "Risk 2", "Risk 3"],
  "valuation_analysis": "Analysis of the company's valuation",
  "investment_recommendation": {{
    "rating": "Buy/Hold/Sell",
    "target_price": "price",
    "time_horizon": "Short-term/Medium-term/Long-term",
    "confidence": "percentage"
  }},
  "conclusion": "Final thoughts on the investment opportunity"
}}
"""
        
        # Call Groq API
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a professional equity research analyst at a top investment bank."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2048
        )
        
        # Parse the response
        thesis_text = response.choices[0].message.content
        
        # Extract JSON from the response
        try:
            # Find JSON in the response (it might be wrapped in markdown code blocks)
            if "```json" in thesis_text:
                json_str = thesis_text.split("```json")[1].split("```")[0].strip()
            elif "```" in thesis_text:
                json_str = thesis_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = thesis_text
            
            thesis = json.loads(json_str)
            
            # Add timestamp
            thesis['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            return thesis
        
        except json.JSONDecodeError:
            # If JSON parsing fails, return the raw text
            return {
                'error': 'Failed to parse AI response as JSON',
                'raw_thesis': thesis_text,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
    
    except Exception as e:
        print(f"Error generating investment thesis for {symbol}: {e}")
        return {'error': str(e)}
