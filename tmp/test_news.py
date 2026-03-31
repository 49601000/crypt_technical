import sys
import os
sys.path.append(os.getcwd())
from src.data.crypt_news_loader import _fetch_yf_news, _fetch_massive_news, _translate_titles_batch

def test_fetch():
    symbol = "BTC-USD"
    print(f"Testing fetch for {symbol}...")
    
    yf_news = _fetch_yf_news(symbol, 5, None)
    print(f"yfinance fetched: {len(yf_news)}")
    
    massive_news = _fetch_massive_news(symbol, 5, None)
    print(f"Massive fetched: {len(massive_news)}")
    
    combined = yf_news + massive_news
    print(f"Combined count: {len(combined)}")
    
    # 翻訳テスト
    if combined:
        print("Translating first 2 items...")
        translated = _translate_titles_batch(combined[:2])
        for i, item in enumerate(translated):
            print(f"Item {i+1} Title: {item['title'][:30]}...")
            print(f"Item {i+1} JP:    {item.get('title_jp', 'N/A')}")

if __name__ == "__main__":
    test_fetch()
