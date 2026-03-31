import yfinance as yf
import pandas as pd
from typing import Dict, List, Any, Optional
from src.utils.crypt_dic_error import get_error_response

# デフォルト設定 (通貨ごとのティッカーと丸め精度)
COIN_CONFIG = {
    "sol": {"tickers": ["SOL-JPY", "SOL-USD"], "precision": 2},
    "hbar": {"tickers": ["HBAR-JPY", "HBAR-USD"], "precision": 4}
}

def get_ticker_df(ticker_symbol: str, period: str = "300d") -> pd.DataFrame:
    """
    yfinance を使用して任意のティッカーの最新価格データを DataFrame で取得します。
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        # SMA 200を計算可能にするためデフォルトで300日分取得
        df = ticker.history(period=period)
        if df.empty:
            raise ValueError(f"No data found for {ticker_symbol}")
        return df
    except Exception as e:
        print(f"Error fetching data for {ticker_symbol}: {e}")
        return pd.DataFrame()

def verify_data_integrity(df: pd.DataFrame, min_rows: int = 200) -> Optional[Dict[str, Any]]:
    """
    取得したデータの整合性をチェックし、不足している場合はエラーレスポンスを返します。
    """
    if df is None or df.empty:
        return get_error_response("No data provided", "データが空であるか、取得できませんでした。")
    
    if len(df) < min_rows:
        return get_error_response(
            "Insufficient data rows",
            f"必要な{min_rows}行のデータが取得できませんでした。(取得行数: {len(df)})"
        )
    return None

def fetch_crypto_prices(coin_key: str, period: str = "300d") -> Dict[str, List[float]]:
    """
    指定された通貨（SOL, HBAR等）の価格データを yfinance から取得します。
    """
    config = COIN_CONFIG.get(coin_key.lower())
    if not config:
        print(f"Error: Unsupported coin key '{coin_key}'")
        return {}

    results: Dict[str, List[float]] = {}
    for symbol in config["tickers"]:
        try:
            ticker = yf.Ticker(symbol)
            # SMA 200を計算可能にするためデフォルトで300日分取得
            df: pd.DataFrame = ticker.history(period=period)

            if df.empty or 'Close' not in df.columns:
                print(f"Warning: No data found for {symbol}.")
                results[symbol] = []
                continue

            # 終値を抽出し、指定された精度で丸める
            processed_prices: List[float] = (
                df.sort_index(ascending=True)['Close']
                .round(config["precision"])
                .tolist()
            )
            results[symbol] = processed_prices

        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            results[symbol] = []

    return results

def fetch_sol_data() -> Dict[str, Dict[str, List[float]]]:
    """旧 datafetch_sol.py の互換用関数"""
    return {"sol": fetch_crypto_prices("sol")}

def fetch_hbar_data() -> Dict[str, Dict[str, List[float]]]:
    """旧 datafetch_hbar.py の互換用関数"""
    # hbarの精度に合わせて取得
    return {"hbar": fetch_crypto_prices("hbar")}

def fetch_all() -> Dict[str, Dict[str, List[float]]]:
    """全サポート通貨のデータを一括で返します"""
    return {
        "sol": fetch_crypto_prices("sol"),
        "hbar": fetch_crypto_prices("hbar")
    }

if __name__ == "__main__":
    # 動作確認用: 新しいフロー (Data -> Analytics -> Judgement)
    from src.logic.crypt_analytics import analyze_market
    from src.logic.crypt_judgement import evaluate_investment

    symbol = "SOL-JPY"
    print(f"--- Processing {symbol} ---")
    
    # 1. FETCH (dataloader)
    df = get_ticker_df(symbol)
    
    if not df.empty:
        # 2. ANALYZE (analytics)
        analysis_res = analyze_market(df)
        
        # 3. JUDGE (judgement)
        decision = evaluate_investment(analysis_res, symbol)
        
        print(f"Final Judgement: {decision['analysis_result']['final_judgement']}")
        print(f"Score: {decision['analysis_result']['technical_score']}")
        print(f"Market Close: {decision['market_snapshot'].get('last_close')}")
        
        if decision['analysis_result']['is_veto_active']:
            print("VETO Reasons:")
            for k, v in decision['analysis_result']['details']['veto_reasons'].items():
                print(f"  - {k}")
    else:
        print("Failed to fetch data.")
