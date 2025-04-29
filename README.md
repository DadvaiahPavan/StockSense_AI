# StockSense - AI-Powered Stock Analysis Platform

StockSense AI — an intelligent, full-stack stock market analysis platform that simplifies investment decisions by integrating real-time data with advanced AI capabilities. Whether you're a beginner or a trader, StockSense AI helps you make informed choices through smart analysis and personalized insights.

##  Overview

StockSense AI is a web-based AI platform that integrates real-time stock market data, sentiment analysis, and large language model intelligence (Groq + LLaMA/Mixtral) to deliver personalized analysis, backtesting tools, and a seamless user interface. It supports both Indian and US stock markets and features a modular architecture designed with Flask, Python, and SQLite.

![StockSense Screenshot](https://i.ibb.co/NgKQpMkh/Screenshot-2025-04-29-165826.png)

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
![Architecture Diagram](images/diagram-export-4-29-2025-4_29_50-PM.png)


## Technologies Used
Flask (Python)

SQLite

Bootstrap 5 + HTML5 + JavaScript

Chart.js for visualizations

yfinance (stock data)

Playwright (news scraping)

Groq API with LLaMA/Mixtral models (AI processing)

Pandas, NumPy, Matplotlib (backtesting tools)

AJAX (async data requests)

dotenv (secure secrets management)


## Project Highlights
Modular Python architecture: service-based organization (stock_service, ai_service, etc.)

Prompt engineering techniques for high-quality AI analysis

Real-time charts & dynamic rendering

Error handling for API limits and scraping timeouts

Plan for future integrations: WebSocket updates, crypto/option modules

## Contributing
We welcome contributions to enhance StockSense AI!

Fork the repo

Create a feature branch (git checkout -b feature/AmazingFeature)

Commit changes (git commit -m 'Add awesome feature')

Push to your branch (git push origin feature/AmazingFeature)

Open a Pull Request

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE.txt) file for details.

## License

MIT
