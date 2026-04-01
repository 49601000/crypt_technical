import os
import sys
import streamlit as st
import pandas as pd
from datetime import datetime

# 単体実行およびルートモジュールの読み込み準備
_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_DIR, "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# 分析対象のティッカーリスト
TICKERS = ["SOL-JPY", "HBAR-JPY", "SOL-USD", "HBAR-USD"]

# ─── 内部モジュールのインポート ───
from output_crypt_tech import get_report_by_ticker, get_full_analysis_report
from output_crypt_news import get_latest_news_from_db
from src.data.crypt_news_loader import update_news_to_db

# ─── ページ設定 / スタイル (cls_main.py から継承) ─────────────────────────

def _setup_style():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500;600&family=Outfit:wght@600;700;800&display=swap');

    :root {
        --bg:       #0f1117;
        --surface:  #1a1d27;
        --card:     #22263a;
        --border:   #2e3452;
        --text:     #e8eaf0;
        --text-2:   #9da3b8;
        --text-3:   #5c6280;
        --accent:   #4f8ef7;
        --green:    #3ecf72;
        --red:      #f05c6e;
        --yellow:   #f5c542;
        --orange:   #f28c38;
    }

    html, body, [class*="css"] {
        font-family: 'Noto Sans JP', sans-serif;
        background-color: var(--bg) !important;
        color: var(--text) !important;
    }
    .stApp, .stApp > div, section.main, .block-container {
        background-color: var(--bg) !important;
    }
    
    .cs-title {
        font-family: 'Outfit', sans-serif;
        font-size: 2.2rem; font-weight: 800;
        color: var(--text); letter-spacing: -0.5px;
        margin-bottom: 0;
    }
    .cs-title span { color: var(--accent); }
    .cs-sub {
        font-size: 0.7rem; letter-spacing: 2px;
        text-transform: uppercase; color: var(--text-3);
        margin-bottom: 1.5rem;
    }

    .score-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        margin-bottom: 0.8rem;
    }
    .score-label {
        font-size: 0.75rem; letter-spacing: 1.5px;
        text-transform: uppercase; color: var(--text-2);
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .score-value {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 3.2rem; font-weight: 700;
        line-height: 1;
    }
    .score-max { font-size: 0.8rem; color: var(--text-3); font-weight: 600; margin-top: 0.3rem; }

    .signal-banner {
        border-radius: 12px; padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
        display: flex; align-items: center; gap: 1rem;
    }
    .signal-icon { font-size: 2.2rem; }
    .signal-text {
        font-family: 'Outfit', sans-serif;
        font-size: 1.2rem; font-weight: 700; color: var(--text);
    }
    .signal-sub { font-size: 0.8rem; color: var(--text-2); font-weight: 600; margin-top: 0.2rem; }

    .price-header {
        background: var(--surface); border: 1px solid var(--border);
        border-radius: 12px; padding: 1.2rem 1.5rem;
        margin-bottom: 1.2rem;
    }
    .price-ticker {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.1rem; font-weight: 600; color: var(--text-2);
        letter-spacing: 0.5px;
    }
    .price-main {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 2.8rem; font-weight: 700; margin-top: 0.8rem;
        letter-spacing: -1px;
    }

    .metric-grid {
        display: grid; grid-template-columns: 1fr 1fr 1fr;
        gap: 0.8rem; margin-bottom: 1rem;
    }
    .metric-item {
        background: var(--surface); border: 1px solid var(--border);
        border-radius: 10px; padding: 1rem;
        text-align: center;
    }
    .metric-lbl {
        font-size: 0.7rem; letter-spacing: 1.5px;
        text-transform: uppercase; color: var(--text-2);
        font-weight: 700; margin-bottom: 0.4rem;
    }
    .metric-val {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.6rem; font-weight: 700; color: var(--text);
    }

    .cs-table {
        width: 100%; border-collapse: collapse;
        font-size: 0.9rem; table-layout: fixed;
    }
    .cs-table th {
        padding: 10px 12px;
        font-size: 0.65rem; letter-spacing: 2px;
        text-transform: uppercase;
        color: var(--text-3); font-weight: 700;
        background: transparent;
        border-bottom: 1px solid var(--border);
        text-align: left;
    }
    .cs-table tbody tr:nth-child(odd)  { background: var(--surface); }
    .cs-table tbody tr:nth-child(even) { background: var(--card); }
    .cs-table tbody td {
        padding: 12px;
        overflow: hidden; word-break: break-word; border: none;
        vertical-align: top;
    }
    .cs-table td:nth-child(1) { color: var(--text-2); font-weight: 600; width: 25%; }
    .cs-table td:nth-child(2) { font-family: 'IBM Plex Mono', monospace; font-weight: 700; width: 25%; color: var(--accent); }
    .cs-table td:nth-child(3) { color: var(--text-3); font-size: 0.85rem; width: 50%; }

    /* Streamlit Tabs Customization */
    div[data-testid="stTabs"] button {
        font-size: 1rem !important; font-weight: 700 !important;
        color: var(--text-2) !important;
        font-family: 'Outfit', sans-serif !important;
    }
    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: var(--accent) !important;
    }
    .news-card {
        background: var(--surface); border: 1px solid var(--border);
        border-radius: 10px; padding: 1.2rem; margin-bottom: 1rem;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .news-card:hover { 
        border-color: var(--accent);
        transform: translateY(-2px);
    }
    .news-title { font-size: 1.1rem; font-weight: 700; color: var(--text); margin-bottom: 0.5rem; line-height: 1.4; }
    .news-title-jp { color: var(--accent); margin-bottom: 0.4rem; }
    .news-meta { font-size: 0.75rem; color: var(--text-3); font-weight: 600; margin-bottom: 0.8rem; display: flex; gap: 15px; }
    .news-orig { font-size: 0.8rem; color: var(--text-2); opacity: 0.8; }
    </style>
    """, unsafe_allow_html=True)


# ─── ヘルパー ─────────────────────────────────────────────────

def _fmt(x, d=2):
    return "—" if x is None else f"{float(x):.{d}f}"

def _color_score(s):
    if s >= 70: return "#3ecf72"
    if s >= 55: return "#4f8ef7"
    if s >= 40: return "#f5c542"
    return "#f05c6e"

def _signal_style(score):
    if score >= 70: return "background:rgba(62,207,114,.12);border:1px solid #3ecf72;"
    if score >= 55: return "background:rgba(79,142,247,.10);border:1px solid #4f8ef7;"
    if score >= 40: return "background:rgba(245,197,66,.10);border:1px solid #f5c542;"
    return "background:rgba(240,92,110,.12);border:1px solid #f05c6e;"

def _build_table(headers, rows):
    ths  = "".join(f"<th>{h}</th>" for h in headers)
    html = f'<table class="cs-table"><thead><tr>{ths}</tr></thead><tbody>'
    for row in rows:
        cells = "".join(f"<td>{c}</td>" for c in row)
        html += f"<tr>{cells}</tr>"
    html += "</tbody></table>"
    return html


# ─── UI パーツ ───────────────────────────────────────────────

def render_crypto_header(snapshot, timestamp):
    ticker = snapshot.get("ticker", "UNKNOWN")
    close = snapshot.get("last_close", 0)
    period = snapshot.get("data_period", "—")
    
    symbol = "¥" if "JPY" in ticker else "$"
    
    st.markdown(f"""
    <div class="price-header">
      <div class="price-ticker">{ticker} <span style="font-size:0.75rem; color:var(--text-3); margin-left:15px;">Period: {period} / Report: {timestamp}</span></div>
      <div class="price-main">{symbol}{_fmt(close, 2)}</div>
    </div>
    """, unsafe_allow_html=True)


def render_score_tab(judgement, breakdown):
    analysis = judgement["analysis_result"]
    score = analysis["technical_score"]
    final_j = analysis["final_judgement"]
    is_veto = analysis["is_veto_active"]
    
    # 総合スコアカード
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(f"""
        <div class="score-card">
          <div class="score-label">Technical Score</div>
          <div class="score-value" style="color:{_color_score(score)}">{score}</div>
          <div class="score-max">/ 100 pt</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        icon = "🚀" if score >= 70 else "⚖️" if score >= 55 else "⚠️"
        style = _signal_style(score)
        st.markdown(f"""
        <div class="signal-banner" style="{style}">
          <div class="signal-icon">{icon}</div>
          <div>
            <div class="signal-text">判断: {final_j}</div>
            <div class="signal-sub">テクニカル指標の統合スコアリングによる判定</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        
        if is_veto:
            reasons = analysis["details"].get("veto_reasons", {})
            reason_str = " | ".join(reasons.values())
            st.error(f"🚨 **VETO 発動中**: {reason_str}")
        elif score >= 70:
            st.success("✨ 市場環境は良好。強力な買いシグナルを検知。")

    st.markdown("---")
    st.markdown("##### 📊 スコア内訳 (Layered Analysis)")
    
    # レイヤー別スコアの表示
    col_t, col_o, col_tr = st.columns(3)
    
    layers = {
        "trend": ("📈 Trend", col_t),
        "oscillator": ("🧮 Momentum", col_o),
        "trust": ("🛡️ Trust", col_tr)
    }
    
    for key, (label, col) in layers.items():
        ls = breakdown.get(key, {})
        l_score = ls.get("score", 0)
        with col:
            st.markdown(f"""
            <div class="metric-item">
              <div class="metric-lbl">{label}</div>
              <div class="metric-val" style="color:{_color_score(l_score)}">{l_score}</div>
            </div>
            """, unsafe_allow_html=True)
            # 内訳の表示
            details = ls.get("details", {})
            for item, pts in details.items():
                st.caption(f"・{item}: +{pts}")


def render_analysis_tab(indicators, descriptions):
    st.markdown("##### 🔍 テクニカル指標詳細")
    
    rows = []
    # 重要そうな順にソート (あるいはそのまま)
    for k, v in indicators.items():
        desc = descriptions.get(k, "（説明なし）")
        rows.append((k, _fmt(v, 4), desc))
    
    st.markdown(_build_table(["指標", "数値", "解説・意味"], rows), unsafe_allow_html=True)


def render_news_tab(ticker):
    """
    st.session_state.news_list に格納されたニュースを表示します。
    """
    if "news_list" not in st.session_state:
        st.info("← サイドバーから『Run Analysis』をクリックして、最新情報を取得してください。")
        return

    news_list = st.session_state.news_list
    
    if not news_list:
        st.warning("⚠️ **ニュースが見つかりません**")
        st.info("DB内にニュースが見つかりません。`crypt_news_loader.py` を実行して、最新のニュースをデータベースに蓄積してください。")
        return

    st.markdown("##### 📰 仮想通貨ニュース (DBから取得)")
    
    # 感情分析アイコンの定義
    sentiment_icons = {
        "positive": "🟢",
        "negative": "🔴",
        "neutral": "⚪"
    }
    
    for item in news_list:
        sentiment = item.get("sentiment", "neutral")
        icon = sentiment_icons.get(sentiment, "⚪")
        
        st.markdown(f"""
        <div class="news-card">
            <div class="news-title">
                <a href="{item['url']}" target="_blank" style="text-decoration:none; color:inherit;">
                    {icon} {item['title']}
                </a>
            </div>
            <div class="news-meta">
                <span>📅 {item['display_date']}</span>
                <span>📡 {item['source']}</span>
                <span>📊 Score: {item.get('score', 0):.2f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Load More ボタン
    if len(news_list) < 100:
        col_btn, col_info = st.columns([1, 2])
        with col_btn:
            if st.button("Load More (さらに20件表示)", use_container_width=True):
                new_limit = st.session_state.get("news_limit", 20) + 20
                st.session_state.news_limit = new_limit
                
                with st.spinner("追加分を取得中..."):
                    new_items = get_latest_news_from_db(ticker, limit=new_limit)
                    
                    if len(new_items) > len(news_list):
                        st.session_state.news_list = new_items
                        st.toast(f"{len(new_items) - len(news_list)}件の新しいニュースを追加しました。")
                        st.rerun()
                    else:
                        st.warning("これ以上のニュースは見つかりませんでした。")
    else:
        st.info("表示上限(100件)に達しました。")

def render_crypto_report(report):
    """
    output_crypt_tech.py の get_full_analysis_report() の戻り値を表示します。
    """
    _setup_style()
    
    if not report:
        st.warning("⚠️ 表示する分析データがありません。")
        return

    # データを安全に取得
    judgement = report.get("level_1_judgement", {})
    breakdown = report.get("level_2_score", {})
    indicators = report.get("level_3_indicators", {})
    descriptions = report.get("descriptions", {})
    
    # judgement が空の場合はエラー表示
    if not judgement:
        st.error("🚨 分析結果 (Judgement) の取得に失敗しました。")
        return
    
    st.markdown('<div class="cs-title">crypto<span>SIGNAL</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="cs-sub">Technical Scoring Skin — Classic Style</div>', unsafe_allow_html=True)
    
    # 各コンポーネントをレンダリング（snapshot も安全に取得）
    snapshot = judgement.get("market_snapshot", {})
    timestamp = judgement.get("timestamp", "—")
    render_crypto_header(snapshot, timestamp)
    
    tab_score, tab_analysis, tab_news = st.tabs(["🎯 score", "🔍 analysis", "📰 news"])
    
    with tab_score:
        render_score_tab(judgement, breakdown)
        
    with tab_analysis:
        render_analysis_tab(indicators, descriptions)
    
    with tab_news:
        # ニュース表示は正規化済みティッカーを優先使用
        target_ticker = snapshot.get("normalized_ticker") or snapshot.get("ticker", "UNKNOWN")
        render_news_tab(target_ticker)

def run():
    """Streamlit アプリケーションのエントリーポイント"""
    st.set_page_config(page_title="Crypto Signal Runner", layout="wide")
    
    if get_full_analysis_report is None:
        st.error("分析モジュール (output_crypt_tech.py) が見つかりません。")
        return

    # サイドバーでティッカー設定
    with st.sidebar:
        st.title("Settings")
        ticker = st.selectbox("Ticker", TICKERS)
        period = st.selectbox("Data Period", ["300d", "100d", "1y", "2y"])
        btn = st.button("Run Analysis", use_container_width=True)
        
        st.markdown("---")
        if st.button("♻️ ニュースを更新", use_container_width=True):
            try:
                with st.spinner(f"{ticker} のニュースを取得中..."):
                    # 2. ロジック実行 (DB保存件数を取得)
                    added_count = update_news_to_db(ticker)
                    
                    # 3. ユーザーフィードバック
                    if added_count > 0:
                        st.toast(f"✅ {added_count}件の新しいニュースを仕入れました！")
                    else:
                        st.toast("☁️ 新しいニュースはありませんでした（最新の状態です）")
                    
                    # 4. 画面更新
                    st.rerun()
            except Exception as e:
                st.error(f"ニュースの更新中にエラーが発生しました: {e}")

    if btn or "report" in st.session_state:
        if btn:
            with st.spinner(f"Analyzing {ticker}..."):
                # 1. テクニカルレポートの取得
                report = get_report_by_ticker(ticker, period)
                if report:
                    st.session_state["report"] = report
                else:
                    st.error("データの取得または分析に失敗しました。")
                    return
                
                # 2. ニュース初期データの取得 (セッション最適化)
                snapshot = report.get("level_1_judgement", {}).get("market_snapshot", {})
                query_ticker = snapshot.get("normalized_ticker") or ticker
                st.session_state.news_limit = 20
                st.session_state.news_list = get_latest_news_from_db(query_ticker, limit=20)
        
        render_crypto_report(st.session_state["report"])
    else:
        st.info("← サイドバーからティッカーを入力して『Run Analysis』をクリックしてください。")

if __name__ == "__main__":
    run()
