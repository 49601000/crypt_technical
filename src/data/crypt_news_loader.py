import sys
import os
from pathlib import Path

# --- パス設定 (ProjectRoot を sys.path に追加) ---
_ROOT_DIR = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

import requests
import yfinance as yf
import streamlit as st
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Union, Optional
from googletrans import Translator
from src.utils.crypt_dic_error import get_error_response
from src.logic.crypt_sentiment_models import SessionLocal, Article
from src.logic.crypt_sentiment import process_article_data

# ─── 設定 ───────────────────────────────────────────────────

MASSIVE_NEWS_URL = "https://api.massive.com/v1/benzinga/v2/news"
JST = timezone(timedelta(hours=9))
SEPARATOR = " ||| "
NEWS_TICKER_OVERRIDES = {
    "SOL-JPY": "SOL-USD",
    "HBAR-JPY": "HBAR-USD",
}
_YF_CACHE_CONFIGURED = False

# ─── 内部ヘルパー ───────────────────────────────────────────

def _utc_to_jst(dt: datetime) -> datetime:
    """UTCのdatetimeをJSTに変換します。"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(JST)

def _format_display_date(dt: datetime) -> str:
    """表示用の日付文字列を生成します。"""
    return dt.strftime("%Y/%m/%d %H:%M") + " (JST)"

def _normalize_news_symbol(symbol: str) -> str:
    """
    ニュース取得に使うシンボルを正規化します。
    要件:
      - SOL-JPY  -> SOL-USD
      - HBAR-JPY -> HBAR-USD
    """
    if not symbol:
        return symbol
    return NEWS_TICKER_OVERRIDES.get(symbol.upper(), symbol.upper())

def _normalize_base_ticker(ticker: str) -> str:
    """DB保存や分析用のベースティッカー（例: SOL）へ正規化します。"""
    if not ticker:
        return ticker
    return ticker.upper().split("-")[0].replace(".T", "")

def _attach_normalized_symbol_meta(
    news_list: List[Dict[str, Any]],
    request_symbol: str,
    normalized_symbol: str,
) -> List[Dict[str, Any]]:
    """ニュース返却データへシンボル正規化情報を付与します。"""
    normalized_ticker = _normalize_base_ticker(normalized_symbol)
    for item in news_list:
        item["request_symbol"] = request_symbol
        item["normalized_symbol"] = normalized_symbol
        item["normalized_ticker"] = normalized_ticker
    return news_list

def _configure_yfinance_cache_dir() -> None:
    """
    yfinance のキャッシュ保存先を、書き込み可能なローカルディレクトリへ設定します。
    一部実行環境ではデフォルト保存先に書き込めず、ニュース取得が失敗するための対策です。
    """
    global _YF_CACHE_CONFIGURED
    if _YF_CACHE_CONFIGURED:
        return

    try:
        cache_dir = Path(_ROOT_DIR) / "tmp" / "yfinance-cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        # yfinanceの公開API名は set_tz_cache_location だが、内部で全キャッシュ先を切り替える
        yf.set_tz_cache_location(str(cache_dir))
        _YF_CACHE_CONFIGURED = True
    except Exception as e:
        # 設定失敗時はログのみ。後続の取得処理側で通常の例外ハンドリングに委ねる。
        print(f"yfinance cache setup warning: {e}")

# ─── 翻訳アルゴリズム ───────────────────────────────────────

def _translate_titles_batch(news_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    ニュースのタイトルを一括で日本語に翻訳します。
    """
    if not news_list:
        return news_list

    titles = [n.get("title", "") for n in news_list]
    combined_text = SEPARATOR.join(titles)

    try:
        translator = Translator()
        translation = translator.translate(combined_text, src='en', dest='ja')
        translated_text = translation.text
        
        # セパレーターで分割
        translated_titles = [t.strip() for t in translated_text.split(SEPARATOR.strip())]

        # 件数が一致するかチェック
        if len(translated_titles) == len(news_list):
            for i, news in enumerate(news_list):
                news["title_jp"] = translated_titles[i]
        else:
            # 不整合時は個別翻訳フォールバック
            for news in news_list:
                try:
                    res = translator.translate(news["title"], src='en', dest='ja')
                    news["title_jp"] = res.text
                except Exception:
                    news["title_jp"] = news["title"]  # 失敗時は原文
    except Exception as e:
        print(f"Translation Error: {e}")
        # 全体失敗時は原文をコピー
        for news in news_list:
            news["title_jp"] = news["title"]
            
    return news_list

# ─── データソース 1: Massive API (Benzinga) ──────────────────

def _fetch_massive_news(symbol: str, count: int, before_date: Optional[datetime]) -> List[Dict[str, Any]]:
    """Massive API から Benzinga ニュースを取得します。"""
    try:
        api_key = st.secrets["MASSIVE_API_KEY"]
    except Exception:
        return []

    base_symbol = symbol.split("-")[0].upper()
    
    params = {
        "tickers": base_symbol,
        "pageSize": count
    }
    
    # before_date がある場合は published_until を追加 (ISO 8601形式)
    if before_date:
        # datetime を UTC に変換してから文字列化
        if before_date.tzinfo is not None:
             before_date = before_date.astimezone(timezone.utc)
        params["published_until"] = before_date.strftime("%Y-%m-%dT%H:%M:%SZ")

    headers = {
        "accept": "application/json",
        "X-API-KEY": api_key
    }

    try:
        response = requests.get(MASSIVE_NEWS_URL, params=params, headers=headers, timeout=10)
        
        if response.status_code == 429:
            # エラーレスポンスを返さず、空リストで通知 (上位でエラーハンドリングするため)
            st.warning("Massive API: Rate limit exceeded (5 requests/min). Showing yfinance news only.")
            return []
        
        response.raise_for_status()
        data = response.json()
        articles = data.get("content") or data.get("data") or []
        
        formatted = []
        for a in articles:
            raw_date = a.get("published_at") or a.get("createdAt")
            if raw_date:
                try:
                    dt_utc = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                except ValueError:
                    dt_utc = datetime.now(timezone.utc)
            else:
                dt_utc = datetime.now(timezone.utc)

            dt_jst = _utc_to_jst(dt_utc)
            
            formatted.append({
                "title": a.get("title", "No Title"),
                "url": a.get("url") or a.get("link"),
                "source": "Benzinga (Massive)",
                "published_at": dt_jst,
                "display_date": _format_display_date(dt_jst)
            })
        return formatted

    except Exception as e:
        print(f"Massive API Error: {e}")
        return []

# ─── データソース 2: yfinance ───────────────────────────────

def _fetch_yf_news(symbol: str, count: int, before_date: Optional[datetime]) -> List[Dict[str, Any]]:
    """yfinance からニュースを取得します。"""
    try:
        _configure_yfinance_cache_dir()
        ticker = yf.Ticker(symbol)
        raw_news = ticker.news or []
        
        formatted = []
        for n in raw_news:
            # yfinance v0.2.x+ の新しい構造への対応
            content = n.get("content", {})
            if content:
                # 新しい構造
                title = content.get("title", "No Title")
                
                # canonicalUrl または clickThroughUrl は辞書の場合がある
                url_obj = content.get("canonicalUrl") or content.get("clickThroughUrl")
                if isinstance(url_obj, dict):
                    url = url_obj.get("url")
                else:
                    url = url_obj
                
                source_obj = content.get("provider", {})
                if isinstance(source_obj, dict):
                    source = source_obj.get("displayName", "Yahoo Finance")
                else:
                    source = "Yahoo Finance"
                
                raw_date = content.get("pubDate")
                try:
                    # ISO 8601 形式: 2026-04-01T08:00:00Z
                    dt_utc = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    dt_utc = datetime.now(timezone.utc)
            else:
                # 旧構造
                title = n.get("title", "No Title")
                url = n.get("link")
                source = n.get("publisher", "Yahoo Finance")
                ts = n.get("providerPublishTime")
                if ts:
                    dt_utc = datetime.fromtimestamp(ts, tz=timezone.utc)
                else:
                    dt_utc = datetime.now(timezone.utc)
                
            dt_jst = _utc_to_jst(dt_utc)
            
            if before_date and dt_jst >= _utc_to_jst(before_date):
                continue

            if not url:
                continue

            formatted.append({
                "title": title,
                "url": url,
                "source": source,
                "published_at": dt_jst,
                "display_date": _format_display_date(dt_jst)
            })
        
        return formatted[:count]
    except Exception as e:
        print(f"yfinance News Error: {e}")
        return []

# ─── メイン関数 ────────────────────────────────────────────

def get_crypto_news(
    symbol: str,
    count: int = 20,
    before_date: datetime = None,
    normalize_for_jpy: bool = True,
) -> List[Dict[str, Any]]:
    """
    複数ソースからニュースを取得・統合・翻訳して返却します。
    """
    request_symbol = (symbol or "").upper()
    news_symbol = _normalize_news_symbol(request_symbol) if normalize_for_jpy else request_symbol

    # 1. 各ソースから取得
    massive_res = _fetch_massive_news(news_symbol, count, before_date)
    yf_res = _fetch_yf_news(news_symbol, count, before_date)
    
    # 2. 統合
    combined = massive_res + yf_res
    
    # 3. 重複排除 (URL をキーにする)
    unique_news = []
    seen_urls = set()
    for item in combined:
        url = item.get("url")
        if url and url not in seen_urls:
            unique_news.append(item)
            seen_urls.add(url)
    
    # 4. ソート (published_at の降順)
    unique_news.sort(key=lambda x: x["published_at"], reverse=True)
    
    # 5. 件数制限 (最大 count 件)
    target_news = unique_news[:count]
    
    # 6. 一括翻訳
    translated_news = _translate_titles_batch(target_news)
    translated_news = _attach_normalized_symbol_meta(
        translated_news,
        request_symbol=request_symbol,
        normalized_symbol=news_symbol
    )
    
    return translated_news

def update_news_to_db(ticker: str, count: int = 20) -> int:
    """
    ニュースを取得し、感情分析を行った上でデータベースに保存します。
    新規に保存された記事の件数を返します。
    ※ ticker は正規化済み（例: 'SOL'）であることを想定しています。
    """
    added_count = 0
    normalized_ticker = _normalize_base_ticker(ticker)

    # 1. ニュースの取得 (SOL-JPY/HBAR-JPY などは get_crypto_news 内で USD に正規化)
    fetch_symbol = f"{normalized_ticker}-USD"
    news_list = get_crypto_news(fetch_symbol, count)
    
    if not news_list:
        return 0

    # 2. データベースへの保存
    try:
        with SessionLocal() as session:
            for item in news_list:
                # URLで重複チェック
                exists = session.query(Article).filter(Article.url == item["url"]).first()
                if exists:
                    continue
                
                # 感情分析 (正規化ティッカー付きで処理)
                analyzed = process_article_data({
                    "title": item.get("title", ""),
                    "summary": "",
                    "title_jp": item.get("title_jp"),
                    "lang": "ja" if item.get("title_jp") else "en",
                    "normalized_ticker": item.get("normalized_ticker") or normalized_ticker,
                })
                label = analyzed["sentiment"]
                score = analyzed["score"]
                article_ticker = analyzed.get("normalized_ticker") or normalized_ticker
                analysis_lang = "ja" if item.get("title_jp") else "en"
                
                # 新規記事の作成
                new_article = Article(
                    ticker=article_ticker,
                    title=item["title"],
                    title_jp=item.get("title_jp"),
                    url=item["url"],
                    source=item["source"],
                    published_at=item["published_at"],
                    sentiment=label,
                    score=score,
                    lang=analysis_lang,
                    is_processed=True
                )
                session.add(new_article)
                added_count += 1
            
            if added_count > 0:
                session.commit()
                
    except Exception as e:
        print(f"Error saving news to DB: {e}")
        # 必要に応じて上位に例外を投げるか、エラーレスポンスを検討
        raise e

    return added_count

if __name__ == "__main__":
    # 簡易テスト
    import os
    # テスト時に st.secrets がない場合のダミー
    if not os.path.exists(".streamlit/secrets.toml"):
        print("Note: st.secrets is not configured, Massive API will be skipped.")
    
    test_symbol = "SOL-USD"
    print(f"--- Fetching news for {test_symbol} ---")
    news = get_crypto_news(test_symbol)
    
    if isinstance(news, dict) and news.get("status") == "error":
        print(f"Error: {news['message']}")
    elif not news:
        print("No news found.")
    else:
        for i, n in enumerate(news[:5]): # 最新5件
            print(f"[{i+1}] {n['display_date']} - {n['source']}")
            print(f"    Title: {n.get('title_jp') or n.get('title')}")
            print(f"    URL:   {n['url']}")
            print()
