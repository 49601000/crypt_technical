"""
src/logic/crypt_sentiment.py — 感情分析・関連度スコアリング (DB連携最適化版)
"""
import re
from typing import Optional, Dict, List, Any, Union, Iterable, Generator, TYPE_CHECKING

if TYPE_CHECKING:
    # 循環インポート回避のため、型チェック時のみインポート
    from .crypt_sentiment_models import Article

# ──────────────────────────────────────────
# 定数定義
# ──────────────────────────────────────────

# 判定閾値（クリプト向けに厳格化：0.2超でポジティブ、-0.2未満でネガティブ）
SENTIMENT_THRESHOLD = 0.2

# ──────────────────────────────────────────
# 感情辞書（英語）
# ──────────────────────────────────────────

POSITIVE_EN = {
    "surge", "soar", "rally", "beat", "exceed", "strong", "profit", "growth",
    "upgrade", "bullish", "record", "gain", "rise", "recover", "outperform",
    "boost", "buy", "upbeat", "positive", "expand", "win", "breakout", "high",
    "dividend", "milestone", "partnership", "approval", "launch", "innovation",
    "staking", "mainnet", "listing", "airdrop", "burn", "whale_buy",
}

NEGATIVE_EN = {
    "fall", "drop", "decline", "miss", "loss", "weak", "cut", "downgrade",
    "bearish", "crash", "plunge", "sell", "layoff", "recall", "lawsuit",
    "fine", "fraud", "risk", "warning", "concern", "low", "disappoint",
    "below", "short", "debt", "bankrupt", "resign", "probe", "investigation",
    "exploit", "scam", "fud", "liquidation", "hack", "dump",
}

# ──────────────────────────────────────────
# 感情辞書（日本語）
# ──────────────────────────────────────────

POSITIVE_JA = {
    "上昇", "急騰", "最高値", "増益", "増収", "好調", "黒字", "買い",
    "上方修正", "復活", "回復", "好業績", "成長", "利益", "配当",
    "新高値", "突破", "強気", "躍進", "拡大", "取得", "契約", "承認",
    "ステーキング", "上場", "メインネット", "エアドロップ", "バーン", "クジラ買い",
}

NEGATIVE_JA = {
    "下落", "急落", "最安値", "減益", "減収", "不調", "赤字", "売り",
    "下方修正", "損失", "リストラ", "解雇", "訴訟", "不正", "懸念",
    "リスク", "警告", "破綻", "辞任", "調査", "問題", "赤字転落",
    "脆弱性", "詐欺", "強制ロスカット", "売り浴びせ", "ハッキング",
}

# 強調修飾語（スコアを増幅）
AMPLIFIERS_EN = {"very", "extremely", "significantly", "massively", "sharply"}
AMPLIFIERS_JA = {"大幅", "急激", "著しく", "大きく"}

# ──────────────────────────────────────────
# 関連キーワードマップ
# ──────────────────────────────────────────

RELEVANT_KEYWORDS: Dict[str, List[str]] = {
    "SOL": ["SOL", "Solana", "ソラナ"],
    "HBAR": ["HBAR", "Hedera", "ヘデラ"],
    "BTC": ["BTC", "Bitcoin", "ビットコイン"],
    "ETH": ["ETH", "Ethereum", "イーサリアム"],
}

# ──────────────────────────────────────────
# 内部ロジック
# ──────────────────────────────────────────

def _count_keywords(text: str, pos_set: set, neg_set: set) -> tuple[int, int]:
    """テキスト内のポジティブ・ネガティブ単語数をカウント"""
    words = re.findall(r"\w+", text.lower())
    pos_count = sum(1 for w in words if w in pos_set)
    neg_count = sum(1 for w in words if w in neg_set)
    # 日本語は文字単位でのマッチング
    for kw in pos_set:
        if len(kw) > 1 and kw in text:
            pos_count += 1
    for kw in neg_set:
        if len(kw) > 1 and kw in text:
            neg_count += 1
    return pos_count, neg_count

def analyze_sentiment(text: str, lang: str = "en") -> tuple[str, float]:
    """
    感情分析。
    Returns:
        (label, score)  label: "positive"|"negative"|"neutral"
                        score: -1.0〜1.0
    """
    if not text:
        return "neutral", 0.0

    if lang == "ja":
        pos_count, neg_count = _count_keywords(text, POSITIVE_JA, NEGATIVE_JA)
    else:
        pos_count, neg_count = _count_keywords(text, POSITIVE_EN, NEGATIVE_EN)

    total = pos_count + neg_count
    if total == 0:
        return "neutral", 0.0

    score = (pos_count - neg_count) / total  # -1.0〜1.0

    if score > SENTIMENT_THRESHOLD:
        return "positive", round(score, 3)
    elif score < -SENTIMENT_THRESHOLD:
        return "negative", round(score, 3)
    else:
        return "neutral", round(score, 3)

# ──────────────────────────────────────────
# 公開API（DB連携用）
# ──────────────────────────────────────────

def is_relevant(title: str, ticker: str) -> bool:
    """タイトルが指定した通貨に関連しているかチェック"""
    target_ticker = ticker.upper().replace(".T", "")
    keywords = RELEVANT_KEYWORDS.get(target_ticker, [target_ticker])
    title_upper = title.upper()
    return any(kw.upper() in title_upper for kw in keywords)

def process_article_data(article: Union[Dict[str, Any], "Article"]) -> Dict[str, Any]:
    """
    1件の記事データ（またはモデル）を処理し、DB更新用の辞書を返す。
    """
    # dict または SQLAlchemyモデルからの属性取得に対応
    if isinstance(article, dict):
        a_id      = article.get("id")
        title     = article.get("title", "")
        summary   = article.get("summary", "")
        title_jp  = article.get("title_jp")
        lang      = article.get("lang", "en")
    else:
        a_id      = getattr(article, "id", None)
        title     = getattr(article, "title", "")
        summary   = getattr(article, "summary", "")
        # モデルに title_jp カラムがない場合は None
        title_jp  = getattr(article, "title_jp", None)
        lang      = getattr(article, "lang", "en")

    # 言語別テキストの選択
    # 日本語設定で翻訳がある場合は優先的に日本語辞書を使用
    if lang == "ja" and title_jp:
        target_text = f"{title_jp} {summary or ''}"
        analysis_lang = "ja"
    elif lang == "ja":
        target_text = f"{title} {summary or ''}"
        analysis_lang = "ja"
    else:
        target_text = f"{title} {summary or ''}"
        analysis_lang = "en"

    label, score = analyze_sentiment(target_text, analysis_lang)

    # Articleモデルの更新用カラム名に合わせた辞書
    return {
        "id":           a_id,
        "sentiment":    label,
        "score":        score,
        "is_processed": True
    }

def batch_analyze_sentiment(articles: Iterable[Union[Dict[str, Any], "Article"]]) -> Generator[Dict[str, Any], None, None]:
    """
    複数の記事を一括で感情分析するジェネレータ。
    """
    for article in articles:
        yield process_article_data(article)

def enrich_articles(articles: List[Any]) -> List[Dict[str, Any]]:
    """
    ArticleDataリスト（またはモデルリスト）に感情スコアを付与して返す（互換性維持用）。
    """
    return list(batch_analyze_sentiment(articles))
