# StockSense - AI-Powered Stock Analysis Platform

StockSense AI — an intelligent, full-stack stock market analysis platform that simplifies investment decisions by integrating real-time data with advanced AI capabilities. Whether you're a beginner or a trader, StockSense AI helps you make informed choices through smart analysis and personalized insights.

##  Overview

StockSense AI is a web-based AI platform that integrates real-time stock market data, sentiment analysis, and large language model intelligence (Groq + LLaMA/Mixtral) to deliver personalized analysis, backtesting tools, and a seamless user interface. It supports both Indian and US stock markets and features a modular architecture designed with Flask, Python, and SQLite.

![StockSense AI](https://i.ibb.co/7NVC0sv/Screenshot-2024-12-28-142055.png)

## Live Demo




##  Key Functional Features

📊 Real-Time Stock Data: View US/India stock prices with dynamic visualizations

🤖 AI Analysis: Generate personalized summaries including technicals, outlook, and risk

💬 AI Chatbot: Chat-driven assistant powered by LLaMA or Mixtral for stock questions

📈 Strategy Backtesting: Build and test custom strategies with historical data

🔍 News Scraping & Sentiment: Scrapes financial news using Playwright and returns AI-based sentiment scores

📂 Portfolio & Watchlist: Save and manage your own portfolio and tracked stocks

🔐 Secure Auth: User login, password hashing, CSRF & SQL injection protection

📱 Responsive UI: Built with Bootstrap, AJAX, and Chart.js for charts

##  Architecture
![StockSense AI](https://i.ibb.co/p6MngcY4/diagram-export-4-29-2025-4-29-50-PM.png)

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Install Playwright browsers:
   ```
   playwright install
   ```
4. Create a `.env` file with your Groq API key:
   ```
   GROQ_API_KEY=your_api_key_here
   ```
5. Run the application:
   ```
   python app.py
   ```
6. Access the application at `http://localhost:5000`

## Project Structure

- `/static` - CSS, JS, and image assets
- `/templates` - HTML templates
- `/services` - AI agents and data services
- `app.py` - Main Flask application
- `init_db.py` - Database initialization
- `schema.sql` - Database schema

## Detailed Documentation

For a comprehensive explanation of the project architecture, implementation details, and how each feature works, please see the [Project Report](project_report.md).

## License

MIT
