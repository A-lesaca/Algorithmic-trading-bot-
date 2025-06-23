# 📈 RSI-Based Alpaca Trading Bot

This a Python algorithmic paper trading bot that measures the  **Relative Strength Index (RSI)** strategy to automate buy/sell decisions using market data from Yahoo Finance and Alpaca's API. The bot trading activity is managed  in a  SQL database for monitoring.

---

## 🚀 Features

- 🧠 **RSI Strategy**: Buy low, sell high using the classic RSI technical indicator.
- 📊 **Real-Time Data**: Uses Yahoo Finance and Alpaca’s free historical data API.
- 💼 **Alpaca Integration**: Submit real buy/sell orders with Alpaca’s trading platform (paper/live).
- 📦 **Database Logging**: Logs trade signals and orders into a MySQL or SQLite database.

---

## 🛠 Requirements

- Python 3.9+
- MySQL server (or use SQLite for local testing)
- For install the requirements please remember to make it through a venv
  
---

### 🐍 Python Dependencies

Install dependencies via:

```bash
pip install -r requirements.txt

alpaca-trade-api
sqlalchemy
yfinance
pandas
rich
pymysql
```
# Trading Bot Setup Guide

## 🦙 How to Create Alpaca API Keys

### Steps:

1. **Create an Alpaca Account**
   - Go to [https://alpaca.markets](https://alpaca.markets)
   - Sign up for a free paper trading account

2. **Navigate to API Keys**
   - Go to your Alpaca Dashboard
   - Click on "Paper Trading" (or "Live Trading" if using real funds)
   - Click on "API Keys"

3. **Copy Your Credentials**
   You'll get two keys:
   - `API Key ID` → Use as `ALPACA_API_KEY`
   - `Secret Key` → Use as `ALPACA_API_SECRET`

---

## 🗃️ How to Create SQL Database

### Installation
```bash
sudo apt install mysql-server
```

### 🗃️ How to create SQL database
### Database setup
```CREATE DATABASE trading_bot;
CREATE USER 'trading_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON trading_bot.* TO 'trading_user'@'localhost';
FLUSH PRIVILEGES;
```
### Connection string
```
DB_URL = "mysql+pymysql://trading_user:your_password@localhost:3306/trading_bot"

```



# 📒 Logging & Output

### Features 
- Logs to both logs/trading_bot.log and the terminal using rich
- Signal summaries printed as styled tables in the terminal

# Trading Bot Documentation

## 📊 System Output Examples

### Terminal Display
```
┌───────────────┬─────────────┐
│    Symbol     │   Signal    │
├───────────────┼─────────────┤
│     AAPL      │    BUY      │
│     MSFT      │    HOLD     │
│     TSLA      │    SELL     │
└───────────────┴─────────────┘
```


```
mysql> SHOW TABLES;
+-----------------------+
| Tables_in_trading_bot |
+-----------------------+
| orders                |
| trade_signals         |
| trades                |
+-----------------------+
```

```
mysql> DESCRIBE trade_signals;
+-----------+-------------+------+-----+---------+----------------+
| Field     | Type        | Null | Key | Default | Extra          |
+-----------+-------------+------+-----+---------+----------------+
| id        | int         | NO   | PRI | NULL    | auto_increment |
| symbol    | varchar(10) | NO   |     | NULL    |                |
| signal    | varchar(10) | NO   |     | NULL    |                |
| rsi       | float       | NO   |     | NULL    |                |
| timestamp | datetime    | YES  |     | NULL    |                |
+-----------+-------------+------+-----+---------+----------------+
```


