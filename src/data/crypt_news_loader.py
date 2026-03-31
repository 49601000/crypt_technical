import requests
import yfinance as yf
import streamlit as st
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Union, Optional
from googletrans import Translator
from src.utils.crypt_dic_error import get_error_response

# ─── 設定 ───────────────────────────────────────────────────

MASSIVE_NEWS_URL = "https://api.massive.com/v1/benzinga/v2/news"
JST = timezone(timedelta(hours=9))
SEPARATOR = " ||| "

# ─── 内部ヘルパー ───────────────────────────────────────────

def _utc_to_jst(dt: datetime) -> datetime:
    """UTCのdatetimeをJSTに変換します。"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(JST)

def _format_display_date(dt: datetime) -> str:
    """表示用の日付文字列を生成します。"""
    return dt.strftime("%Y/%m/%d %H:%M") + " (JST)"

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
        ticker = yf.Ticker(symbol)
        yf_news = ticker.news or []
        
        formatted = []
        for n in yf_news:
            ts = n.get("providerPublishTime")
            if ts:
                dt_utc = datetime.fromtimestamp(ts, tz=timezone.utc)
            else:
                dt_utc = datetime.now(timezone.utc)
                
            dt_jst = _utc_to_jst(dt_utc)
            
            # before_date によるフィルタリング
            if before_date and dt_jst >= _utc_to_jst(before_date):
                continue

            formatted.append({
                "title": n.get("title", "No Title"),
                "url": n.get("link"),
                "source": n.get("publisher", "Yahoo Finance"),
                "published_at": dt_jst,
                "display_date": _format_display_date(dt_jst)
            })
        
        # 件数制限
        return formatted[:count]
    except Exception as e:
        print(f"yfinance News Error: {e}")
        return []

# ─── メイン関数 ────────────────────────────────────────────

def get_crypto_news(symbol: str, count: int = 20, before_date: datetime = None) -> List[Dict[str, Any]]:
    """
    複数ソースからニュースを取得・統合・翻訳して返却します。
    """
    # 1. 各ソースから取得
    massive_res = _fetch_massive_news(symbol, count, before_date)
    yf_res = _fetch_yf_news(symbol, count, before_date)
    
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
    
    return translated_news

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
    else:
        for i, n in enumerate(news[:5]): # 最新5件
            print(f"[{i+1}] {n['display_date']} - {n['source']}")
            print(f"    Title: {n['title']}")
            print(f"    URL:   {n['url']}")
            print()
