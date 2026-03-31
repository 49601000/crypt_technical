"""
output_crypt_news.py — UI表示用ニュース取得モジュール
"""
from typing import List, Dict, Any
# プロジェクト構成に合わせて src.logic からインポート
from src.logic.crypt_sentiment_models import SessionLocal, Article
from sqlalchemy import desc

def get_latest_news_from_db(ticker: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    データベースから特定のティッカーに関連する最新のニュース記事を取得し、
    UI表示に適した辞書形式のリストで返却します。
    """
    # ティッカーを大文字に正規化
    normalized_ticker = ticker.upper()
    news_list = []
    
    try:
        # Context Manager を使用してセッションを確実にクローズ
        with SessionLocal() as session:
            articles = (
                session.query(Article)
                .filter(Article.ticker == normalized_ticker)
                .order_by(desc(Article.published_at))
                .limit(limit)
                .all()
            )
            
            for a in articles:
                # published_at を YYYY-MM-DD HH:MM 形式に変換
                display_date = (
                    a.published_at.strftime("%Y-%m-%d %H:%M") 
                    if a.published_at else "Unknown Date"
                )
                
                # 指定されたキーを含む辞書を構築
                news_list.append({
                    "title":        a.title,
                    "url":          a.url,
                    "sentiment":    a.sentiment,
                    "score":        a.score,
                    "source":       a.source,
                    "summary":      a.summary,
                    "display_date": display_date,
                    # 以下は利便性のための追加フィールド
                    "id":           a.id,
                    "ticker":       a.ticker,
                    "lang":         a.lang,
                })
    except Exception as e:
        print(f"Error fetching news from DB: {e}")
        # エラー時も空リストを返却してクラッシュを防ぐ
        return []
            
    return news_list

if __name__ == "__main__":
    # 簡易テストコード
    test_tickers = ["SOL", "BTC", "ETH"]
    
    for ticker in test_tickers:
        print(f"\n--- Fetching latest news for {ticker} ---")
        results = get_latest_news_from_db(ticker, limit=3)
        
        if not results:
            print(f"No news found for {ticker} in DB.")
        else:
            for i, res in enumerate(results):
                label = res.get('sentiment') or 'neutral'
                score = res.get('score') or 0.0
                print(f"[{i+1}] {res['display_date']} | {label.upper()} ({score})")
                print(f"    Title:  {res['title']}")
                print(f"    Source: {res['source']}")
                print(f"    URL:    {res['url']}")
