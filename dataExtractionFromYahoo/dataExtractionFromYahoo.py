import yfinance as yf
import json
import boto3
from datetime import datetime

def get_financial_data(symbol):

    # Téléchargement des données via yfinance
    ticker = yf.Ticker(symbol)
    info = ticker.info
    
    # Données principales
    share_price = info.get("currentPrice") or info.get("regularMarketPrice")
    eps = info.get("trailingEps") or info.get("forwardEps")
    
    # Stock Return sur 1 an
    history = ticker.history(period="1y")
    stock_return = (history["Close"].iloc[-1] / history["Close"].iloc[0]) - 1 if len(history) > 1 else None
    
    # Market Return (S&P 500)
    sp500 = yf.Ticker("^GSPC").history(period="1y")
    market_return = (sp500["Close"].iloc[-1] / sp500["Close"].iloc[0]) - 1 if len(sp500) > 1 else None
    
    # Regroupement des résultats
    data = {
        "symbol": symbol,
        "timestamp": datetime.now().isoformat(),
        "share_price": share_price,
        "EPS": eps,
        "stock_return_1y": round(stock_return, 4) if stock_return else None,
        "market_return_1y": round(market_return, 4) if market_return else None
    }
    
    return data

if __name__ == "__main__":
    symbol = "AAPL"  # Exemple de symbole
    data = get_financial_data(symbol)

    print(data)
