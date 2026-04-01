import sys
import os
from pathlib import Path

# --- パス設定 ---
_ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from src.data.crypt_news_loader import get_crypto_news

def test_translation():
    symbol = "BTC-USD"
    print(f"Testing translation for {symbol}...")
    news = get_crypto_news(symbol, count=3)
    
    for i, item in enumerate(news):
        print(f"[{i}] Original: {item.get('title')}")
        print(f"    Translated: {item.get('title_jp')}")
        print("-" * 20)

if __name__ == "__main__":
    test_translation()
