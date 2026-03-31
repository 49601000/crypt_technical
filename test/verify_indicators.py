import yfinance as yf
import pandas as pd
from crypt_analytics import calculate_indicators, calculate_technical_score

def verify_with_real_data():
    symbol = "SOL-USD"
    print(f"--- Fetching real data for {symbol} ---")
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="300d")
    
    if df.empty:
        print("Failed to fetch data.")
        return

    print(f"Data fetched: {len(df)} rows.")
    
    indicators = calculate_indicators(df)
    
    print("\n--- Technical Indicators for SOL-USD (Latest) ---")
    for key, value in indicators.items():
        print(f"{key:15}: {value:>12.4f}")

    # スコア計算の追加
    score_res = calculate_technical_score(df)
    
    print(f"\n--- Technical Score: {score_res['total_score']} / 100 ---")
    for layer, data in score_res['breakdown'].items():
        print(f"{layer.capitalize():10}: {data['score']} pts")

    # VETOの追加
    from technical_VETO import check_veto_flags
    vetos = check_veto_flags(df)
    if vetos:
        print("\n--- VETO FLAGS DETECTED! ---")
        for veto_name, reason in vetos.items():
            print(f"[{veto_name}]\n {reason}")
    else:
        print("\n--- No VETO Flags ---")

if __name__ == "__main__":
    verify_with_real_data()
