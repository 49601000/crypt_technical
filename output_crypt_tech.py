import pandas as pd
from typing import Dict, Any
import yfinance as yf

# 内部モジュールのインポート
from src.logic.crypt_analytics import analyze_market
from src.logic.crypt_judgement import evaluate_investment
from src.data.crypt_dataloader import get_ticker_df

def get_indicator_descriptions() -> Dict[str, str]:
    """
    フロントエンド等で利用可能なテクニカル指標の解説辞書を返却します。
    """
    return {
        "SMA": "王道。200日線より上なら「長期強気」とか、ゴールデンクロスで加点する。",
        "EMA": "直近の価格を重視するMA。SOLみたいな動きが早い通貨にはSMAより反応が良い。",
        "ichimoku_cloud": "「雲の上か下か」だけでトレンドを1か0で判定できるから、スコアリングと相性抜群。",
        "ADX": "「トレンドが今、強いのか弱いのか」を数値化（0〜100）する。トレンドの「鮮度」がわかる。",
        "RSI": "言わずと知れた0〜100の数値。30以下で加点（売られすぎ）、70以上で減点（買われすぎ）など。",
        "MACD_hist": "MACDの「勢い」を棒グラフにしたもの。これがプラス圏で増えてるなら加点。",
        "StochRSI": "RSIをさらに敏感にしたもの。RSIが動かないレンジ相場でも細かく反応してくれる。",
        "Bollinger_PB": "価格がバンドのどの位置にいるかを数値化したもの（上が1.0、下が0）。",
        "ATR": "ボラティリティの大きさ。これが急増してたら「祭りが始まった」合図。",
        "OBV": "「価格が上がった時の出来高」を足していく指標。価格は上がってるのにOBVが下がってたら「中身スカスカの上げ」と判断できる。"
    }

def get_full_analysis_report(df: pd.DataFrame, symbol: str = "UNKNOWN") -> Dict[str, Any]:
    """
    1. Judgement (投資判断)
    2. Technical Score (スコアリング)
    3. Technical Analysis (指標データ)
    の3階層を統合したレポートを生成します。
    """
    # 1. 指標計算 & VETOチェック (analytics)
    # これにより、raw_indicators も含めて一括計算される
    analysis_res = analyze_market(df)
    
    # 2. 投資判断 (judgement)
    judgement_result = evaluate_investment(analysis_res, symbol=symbol)
    
    # 階層型レポートの構築
    return {
        "level_1_judgement": judgement_result,
        "level_2_score": analysis_res.get("score_breakdown", {}),
        "level_3_indicators": analysis_res.get("raw_indicators", {}),
        "descriptions": get_indicator_descriptions()
    }

def get_report_by_ticker(ticker: str, period: str = "300d") -> Dict[str, Any]:
    """
    ティッカーシンボルを指定して、データの取得から分析レポートの生成までを一括で行います。
    どのフロントエンド（スキン）からも利用可能な共通インターフェースです。
    """
    df = get_ticker_df(ticker, period)
    if df.empty:
        return {}
    return get_full_analysis_report(df, symbol=ticker)

def print_judgement_report(result: Dict[str, Any]):
    """
    判定結果を人間が読みやすい形式（階層構造を意識）で出力します。
    """
    analysis = result["analysis_result"]
    snapshot = result["market_snapshot"]
    
    print("="*50)
    print(f" SOL-USD 押し目買い判定レポート: {result['timestamp']}")
    print("="*50)
    
    print(f"\n[1] 最終投資判断: >> {analysis['final_judgement']} <<")
    print(f"    - テクニカル総合スコア: {analysis['technical_score']} / 100 pt")
    print(f"    - 最新価格: ${snapshot['last_close']} (データ期間: {snapshot['data_period']})")
    
    if analysis['is_veto_active']:
        print("\n[!] VETO (強制拒否) が発動中:")
        for name, reason in analysis['details']['veto_reasons'].items():
            print(f"    - {name}: {reason}")
    else:
        print("\n[✔] 致命的なリスク (VETO) は検知されませんでした。")

    print("\n[2] スコア内訳 (Layered Details):")
    breakdown = analysis['details']['score_breakdown']
    for layer, data in breakdown.items():
        layer_name = {
            "trend": "環境認識 (Trend)",
            "oscillator": "押し目/過熱感 (Momentum)",
            "trust": "信頼性 (Volatility/Volume)"
        }.get(layer, layer)
        
        print(f"    - {layer_name}: {data['score']} pt")
        for item, pts in data['details'].items():
            print(f"        * {item}: +{pts}")

    print("\n" + "="*50)

if __name__ == "__main__":
    # SOL-USD の実データで実行
    ticker = "SOL-USD"
    print(f"{ticker} の最新マーケットデータを取得中...")
    full_report = get_report_by_ticker(ticker, "300d")
    
    if full_report:
        # 1. Judgement の詳細表示 (既存の表示関数を利用)
        print_judgement_report(full_report["level_1_judgement"])
        
        # 3. Raw Indicators の表示 (簡易)
        print("\n[3] 生データ指標 (Technical Analysis):")
        for k, v in full_report["level_3_indicators"].items():
            print(f"    - {k:15}: {v:>12.4f}")
    else:
        print("分析レポートの生成に失敗しました。")
