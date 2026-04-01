import sys
import os
from pathlib import Path

# --- パス設定 ---
_ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from src.data.crypt_news_loader import update_news_to_db
from src.logic.crypt_sentiment_models import SessionLocal, Article

def verify_fix():
    ticker = "SOL"
    print(f"Testing update_news_to_db for {ticker}...")
    added = update_news_to_db(ticker, count=3)
    print(f"Added {added} news articles.")
    
    with SessionLocal() as session:
        articles = session.query(Article).filter(Article.ticker == ticker).all()
        for i, a in enumerate(articles):
            print(f"[{i}] Ticker: {a.ticker}")
            print(f"    Original Title: {a.title}")
            print(f"    Translated Title: {a.title_jp}")
            print(f"    URL: {a.url}")
            print(f"    Lang: {a.lang}")
            print("-" * 20)
            
            if not a.title_jp and a.lang == "ja":
                print("ERROR: title_jp is missing but lang is 'ja'")
            if a.title_jp:
                print("SUCCESS: title_jp is present.")

if __name__ == "__main__":
    verify_fix()
