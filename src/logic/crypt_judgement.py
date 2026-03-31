import pandas as pd
import pandas_ta as ta
import yfinance as yf
import datetime
from typing import Dict, Any, Optional

# 既存モジュールのインポート
from src.logic.crypt_analytics import analyze_market


def evaluate_investment(analysis_result: Dict[str, Any], symbol: str = "UNKNOWN") -> Dict[str, Any]:
    """
    解析結果(辞書)を受け取り、最終的な投資判断を下します。
    """
    # エラー形式のレスポンスが渡ってきた場合の処理
    if not analysis_result or analysis_result.get("status") == "error":
        error_res = analysis_result if analysis_result else {}
        return {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": symbol,
            **error_res
        }

    # 1. 解析データの取得
    total_score = analysis_result.get("technical_score", 0)
    is_veto = analysis_result.get("is_veto_active", False)
    vetos = analysis_result.get("veto_reasons", {})
    
    # 2. 最終判定の決定ロジック
    judgement = "WATCH"
    if is_veto:
        judgement = "DANGER (VETO)"
    else:
        if total_score >= 80:
            judgement = "GodBuy"
        elif total_score >= 60:
            judgement = "Buy"
        elif total_score >= 40:
            judgement = "Watch"
        else:
            judgement = "Danger"

    # 3. 結果構造の構築
    return {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "symbol": symbol,
        "analysis_result": {
            "final_judgement": judgement,
            "technical_score": total_score,
            "is_veto_active": is_veto,
            "details": {
                "score_breakdown": analysis_result.get("score_breakdown", {}),
                "veto_reasons": vetos if is_veto else {}
            }
        },
        "market_snapshot": {
            **analysis_result.get("market_snapshot", {}),
            "ticker": symbol
        }
    }

if __name__ == "__main__":
    # テスト実行
    symbol = "SOL-USD"
    print(f"--- Fetching data for {symbol} ---")
    df = yf.Ticker(symbol).history(period="300d")
    
    if not df.empty:
        # 1. 分析の実行 (analyticsモジュール)
        analysis_res = analyze_market(df)
        
        # 2. 投資判断の実行 (judgementモジュール)
        result = evaluate_investment(analysis_res, symbol)
        
        print(f"\n[{symbol}] Final Judgement: {result['analysis_result']['final_judgement']}")
        print(f"Technical Score: {result['analysis_result']['technical_score']}")
        
        if result['analysis_result']['is_veto_active']:
            print("\n!!! VETO Flags Detected !!!")
            for key, msg in result['analysis_result']['details']['veto_reasons'].items():
                print(f"- {key}: {msg}")
        
        print("\nDetails:")
        for key, val in result['analysis_result']['details']['score_breakdown'].items():
            print(f"  {key}: {val}")
        
        print(f"\nMarket Snapshot: {result['market_snapshot']}")
    else:
        print("Failed to fetch data.")
