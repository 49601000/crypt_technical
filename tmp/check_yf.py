import yfinance as yf
ticker = yf.Ticker("BTC-USD")
print(f"News: {ticker.news}")
