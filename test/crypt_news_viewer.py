import streamlit as st
import requests
import yfinance as yf
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from googletrans import Translator

# ─── 設定 ───────────────────────────────────────────────────
MASSIVE_API_KEY = "YRCTpjNgCCmabpMcfVJhqF5vpcPc7Fnh"
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
                    news["title_jp"] = news["title"]
    except Exception as e:
        st.error(f"Translation Error: {e}")
        # 全体失敗時は原文をコピー
        for news in news_list:
            news["title_jp"] = news["title"]
            
    return news_list

# ─── データソース 1: Massive API (Benzinga) ──────────────────

def _fetch_massive_news(symbol: str, count: int) -> List[Dict[str, Any]]:
    """Massive API から Benzinga ニュースを取得します。"""
    base_symbol = symbol.split("-")[0].upper()
    
    params = {
        "tickers": base_symbol,
        "pageSize": count
    }
    
    headers = {
        "accept": "application/json",
        "X-API-KEY": MASSIVE_API_KEY
    }

    try:
        response = requests.get(MASSIVE_NEWS_URL, params=params, headers=headers, timeout=10)
        
        if response.status_code == 429:
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
        st.error(f"Massive API Error: {e}")
        return []

# ─── データソース 2: yfinance ───────────────────────────────

def _fetch_yf_news(symbol: str, count: int) -> List[Dict[str, Any]]:
    """yfinance からニュースを取得します。"""
    try:
        ticker = yf.Ticker(symbol)
        raw_news = ticker.news or []
        
        formatted = []
        for n in raw_news:
            content = n.get("content", {})
            if content:
                title = content.get("title", "No Title")
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
                    dt_utc = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    dt_utc = datetime.now(timezone.utc)
            else:
                title = n.get("title", "No Title")
                url = n.get("link")
                source = n.get("publisher", "Yahoo Finance")
                ts = n.get("providerPublishTime")
                if ts:
                    dt_utc = datetime.fromtimestamp(ts, tz=timezone.utc)
                else:
                    dt_utc = datetime.now(timezone.utc)
                
            dt_jst = _utc_to_jst(dt_utc)
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
        st.error(f"yfinance News Error: {e}")
        return []

# ─── メインロジック ────────────────────────────────────────────

def get_crypto_news(symbol: str, count: int = 20) -> List[Dict[str, Any]]:
    """複数ソースからニュースを取得・統合・翻訳して返却します。"""
    massive_res = _fetch_massive_news(symbol, count)
    yf_res = _fetch_yf_news(symbol, count)
    
    combined = massive_res + yf_res
    
    unique_news = []
    seen_urls = set()
    for item in combined:
        url = item.get("url")
        if url and url not in seen_urls:
            unique_news.append(item)
            seen_urls.add(url)
    
    unique_news.sort(key=lambda x: x["published_at"], reverse=True)
    target_news = unique_news[:count]
    translated_news = _translate_titles_batch(target_news)
    
    return translated_news

# ─── Streamlit UI ─────────────────────────────────────────────

def main():
    st.set_page_config(page_title="Crypto News Viewer", page_icon="📰")
    
    st.title("📰 Crypto News Viewer")
    st.markdown("Massive API and Yahoo Finance news retrieval test tool.")

    with st.sidebar:
        st.header("Search Parameters")
        ticker = st.text_input("Ticker Symbol (e.g., SOL, BTC, ETH)", value="SOL")
        count = st.slider("Max News Count", 5, 50, 15)
        fetch_btn = st.button("Fetch News")

    if fetch_btn:
        symbol = f"{ticker.upper()}-USD"
        with st.spinner(f"Fetching news for {symbol}..."):
            news_items = get_crypto_news(symbol, count)
            
            if not news_items:
                st.info("No news articles found.")
            else:
                st.success(f"Found {len(news_items)} news articles.")
                for item in news_items:
                    with st.container():
                        # タイトル (翻訳があればそれを使用)
                        disp_title = item.get("title_jp") or item.get("title")
                        st.subheader(disp_title)
                        
                        # メタ情報
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            st.caption(f"📅 {item['display_date']}")
                        with col2:
                            st.caption(f"🔗 Source: {item['source']}")
                        
                        # リンク
                        st.markdown(f"[Read full article]({item['url']})")
                        
                        # 原文 (翻訳がある場合)
                        if "title_jp" in item and item["title_jp"] != item["title"]:
                            with st.expander("Show original title"):
                                st.write(item["title"])
                        
                        st.divider()

if __name__ == "__main__":
    main()
