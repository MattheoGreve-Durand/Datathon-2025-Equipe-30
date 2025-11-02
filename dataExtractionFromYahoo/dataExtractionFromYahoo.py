import yfinance as yf
from datetime import datetime
import numpy as np

def get_financial_data(symbol):
    ticker = yf.Ticker(symbol)
    info = ticker.info

    # === Données de base ===
    share_price = info.get("currentPrice") or info.get("regularMarketPrice")
    eps = info.get("trailingEps") or info.get("forwardEps")
    beta = info.get("beta")
    tax_rate = info.get("effectiveTaxRate")

    # === Historique 2024 ===
    history = ticker.history(start="2024-01-01", end="2024-12-31")
    stock_return = (
        (history["Close"].iloc[-1] / history["Close"].iloc[0]) - 1 if len(history) > 1 else None
    )

    sp500 = yf.Ticker("^GSPC").history(start="2024-01-01", end="2024-12-31")
    market_return = (
        (sp500["Close"].iloc[-1] / sp500["Close"].iloc[0]) - 1 if len(sp500) > 1 else None
    )

    recommendation_mean = info.get("recommendationMean")
    num_analysts = info.get("numberOfAnalystOpinions")
    recommendation_key = info.get("recommendationKey")

    # === Données de bilan (approximations) ===
    balance_sheet = ticker.balance_sheet
    total_debt = None
    if "TotalDebt" in balance_sheet.index:
        total_debt = balance_sheet.loc["TotalDebt"].iloc[0]

    total_equity = None
    if "TotalStockholderEquity" in balance_sheet.index:
        total_equity = balance_sheet.loc["TotalStockholderEquity"].iloc[0]

    # === Nombre d’actions ===
    shares_outstanding = info.get("sharesOutstanding")
 
    # === Valeur de marché de l’équité (Market Cap) ===
    market_value_equity = (
        share_price * shares_outstanding if share_price and shares_outstanding else None
    )

    # === Valeur de marché de la dette (approximation) ===
    market_value_debt = total_debt if total_debt else None

    # === Valeur totale de marché ===
    total_market_value = (
        market_value_equity + market_value_debt
        if market_value_equity and market_value_debt
        else None
    )

    # === Paramètres de coût du capital ===
    risk_free_rate = 0.045  # 4.5% (modifiable)
    market_premium = market_return - risk_free_rate if market_return else 0.06

    cost_of_equity = (
        risk_free_rate + beta * market_premium if beta and market_return else None
    )

    cost_of_debt = None
    financials = ticker.financials
    if "InterestExpense" in financials.index and total_debt:
        interest_expense = abs(financials.loc["InterestExpense"].iloc[0])
        cost_of_debt = interest_expense / total_debt

    # === Données finales ===
    data = {
        "symbol": symbol,
        "timestamp": datetime(2024, 12, 31, 23, 59, 59).isoformat(),  # <<<<< modifié ici
        "sharePrice": share_price,
        "eps": eps,
        "stockReturn": round(stock_return, 4) if stock_return else None,
        "marketReturn": round(market_return, 4) if market_return else None,
        "recommendationMean": recommendation_mean,
        "numberOfAnalystOpinions": num_analysts,
        "recommendationKey": recommendation_key,
        "Capm": round(cost_of_equity, 4) if cost_of_equity else None,
        "riskFreeRate": risk_free_rate,
        "beta": beta,
        "rm": round(market_return, 4) if market_return else None,
    }

    return data

if __name__ == "__main__":
    symbol = "AAPL"
    data = get_financial_data(symbol)
    print(data)