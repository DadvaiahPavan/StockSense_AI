# StockSense - AI-Powered Stock Analysis Platform

A comprehensive, real-time stock analysis platform with AI-powered insights for both Indian and US markets.

## Features

- 🌟 Beautiful responsive landing page
- 🔐 Secure user authentication system
- 📊 Real-time stock data visualization
- 🤖 AI-powered investment insights using Groq API
- 📈 Strategy builder with backtesting
- 📱 User-specific dashboard with portfolio tracking
- 🌐 Support for both US and Indian markets
- 💬 AI chatbot for market questions and insights

## Tech Stack

- **Frontend**: HTML, CSS, JavaScript, Bootstrap, Chart.js
- **Backend**: Python Flask
- **Authentication**: Flask-Login with SQLite
- **AI Engine**: Groq API (LLaMA or Mixtral models)
- **Data Sources**: 
  - yfinance for real-time stock data
  - Playwright for web scraping (news, sentiment)
- **Database**: SQLite

## Setup Instructions

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
