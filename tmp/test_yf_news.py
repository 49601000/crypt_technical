import yfinance as yf
ticker = yf.Ticker("SOL-USD")
news = ticker.news
print(f"News: {news}")
if news:
    print(f"Number of news items: {len(news)}")
    for n in news[:3]:
        print(n)
else:
    print("No news found.")
