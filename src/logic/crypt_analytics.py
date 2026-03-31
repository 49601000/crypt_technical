import os
import sys
import pandas as pd
import pandas_ta as ta
from typing import Dict, Any, List, Optional

# 単体実行時のインポートパス調整
if __name__ == "__main__":
    _root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if _root not in sys.path:
        sys.path.insert(0, _root)

from src.utils.crypt_dic_error import get_error_response

# カテゴリ別の最小必要行数 (例: SMA 200なら200行)
MIN_ROWS_REQUIRED = 200

# ─── 指標計算セクション (旧 technical_analysis.py) ─────────────────────────

def calculate_indicators(df: pd.DataFrame) -> Dict[str, float]:
    """
    10種類のテクニカル指標を計算し、最新の値を辞書形式で返却します。
    すべての戻り値は小数点第4位で四捨五入されます。
    """
    if df is None or df.empty:
        return _get_default_indicators()

    required_cols = {'open', 'high', 'low', 'close', 'volume'}
    current_cols = {c.lower() for c in df.columns}
    if not required_cols.issubset(current_cols):
        return _get_default_indicators()

    if len(df) < 1:
        return _get_default_indicators()

    df_calc = df.copy()
    df_calc.columns = [c.lower() for c in df_calc.columns]

    results: Dict[str, float] = {}
    results.update(_calculate_trend_indicators(df_calc))
    results.update(_calculate_oscillator_indicators(df_calc))
    results.update(_calculate_volatility_indicators(df_calc))
    results.update(_calculate_momentum_indicators(df_calc))

    return {k: round(v, 4) for k, v in results.items()}

def _get_default_indicators() -> Dict[str, float]:
    return {
        "sma_25": 0.0, "sma_75": 0.0, "sma_200": 0.0,
        "ema": 0.0, "ichimoku_cloud": 0.5, "adx": 0.0,
        "rsi": 50.0, "macd_hist": 0.0, "stoch_rsi": 0.5,
        "bollinger_pb": 0.5, "atr": 0.0, "obv": 0.0
    }

def _calculate_trend_indicators(df: pd.DataFrame) -> Dict[str, float]:
    res = {}
    close = df['close']
    res["sma_25"] = float(ta.sma(close, length=25).iloc[-1]) if len(df) >= 25 else 0.0
    res["sma_75"] = float(ta.sma(close, length=75).iloc[-1]) if len(df) >= 75 else 0.0
    res["sma_200"] = float(ta.sma(close, length=200).iloc[-1]) if len(df) >= 200 else 0.0
    res["ema"] = float(ta.ema(close, length=20).iloc[-1]) if len(df) >= 20 else 0.0
    res["ichimoku_cloud"] = _get_ichimoku_status(df)
    adx_df = ta.adx(df['high'], df['low'], close)
    res["adx"] = float(adx_df.iloc[-1, 0]) if adx_df is not None and not adx_df.empty else 0.0
    return res

def _get_ichimoku_status(df: pd.DataFrame) -> float:
    ichimoku_df, _ = ta.ichimoku(df['high'], df['low'], df['close'])
    if ichimoku_df is None or ichimoku_df.empty:
        return 0.5
    latest_close = df['close'].iloc[-1]
    span_a = ichimoku_df['ISA_9'].iloc[-1]
    span_b = ichimoku_df['ISB_26'].iloc[-1]
    if pd.isna(span_a) or pd.isna(span_b):
        return 0.5
    if latest_close > max(span_a, span_b):
        return 1.0
    if latest_close < min(span_a, span_b):
        return 0.0
    return 0.5

def _calculate_oscillator_indicators(df: pd.DataFrame) -> Dict[str, float]:
    res = {}
    close = df['close']
    rsi = ta.rsi(close, length=14)
    res["rsi"] = float(rsi.iloc[-1]) if rsi is not None and not rsi.empty else 50.0
    macd_df = ta.macd(close)
    res["macd_hist"] = float(macd_df.iloc[-1, 1]) if macd_df is not None and not macd_df.empty else 0.0
    stoch_df = ta.stochrsi(close)
    res["stoch_rsi"] = float(stoch_df.iloc[-1, 0]) if stoch_df is not None and not stoch_df.empty else 0.5
    return res

def _calculate_volatility_indicators(df: pd.DataFrame) -> Dict[str, float]:
    res = {}
    bb_df = ta.bbands(df['close'])
    res["bollinger_pb"] = float(bb_df.iloc[-1, 4]) if bb_df is not None and not bb_df.empty else 0.5
    atr = ta.atr(df['high'], df['low'], df['close'])
    res["atr"] = float(atr.iloc[-1]) if atr is not None and not atr.empty else 0.0
    return res

def _calculate_momentum_indicators(df: pd.DataFrame) -> Dict[str, float]:
    res = {}
    obv = ta.obv(df['close'], df['volume'])
    res["obv"] = float(obv.iloc[-1]) if obv is not None and not obv.empty else 0.0
    return res


# ─── スコア計算セクション (旧 technical_score.py) ─────────────────────────

def calculate_technical_score(df: pd.DataFrame) -> Dict[str, Any]:
    """
    複数レイヤーでのテクニカルスコア (0-100pt) を計算します。
    """
    if df is None or len(df) < 2:
        return {"total_score": 0, "breakdown": {}, "message": "Insufficient data"}

    # 大文字・小文字両対応
    df_calc = df.copy()
    df_calc.columns = [c.capitalize() for c in df_calc.columns]
    
    close = df_calc['Close']
    high = df_calc['High']
    low = df_calc['Low']
    volume = df_calc['Volume']
    
    # 指標の計算
    sma200 = ta.sma(close, length=200)
    sma75 = ta.sma(close, length=75)
    ema20 = ta.ema(close, length=20)
    ichimoku_df, _ = ta.ichimoku(high, low, close)
    adx_df = ta.adx(high, low, close)
    rsi = ta.rsi(close, length=14)
    stoch_df = ta.stochrsi(close)
    macd_df = ta.macd(close)
    bb_df = ta.bbands(close)
    obv = ta.obv(close, volume)
    
    curr_idx = -1
    prev_idx = -2
    
    score_a = 0
    details_a = {}
    
    # --- A. 環境認識レイヤー (40点) ---
    if sma200 is not None and close.iloc[curr_idx] > sma200.iloc[curr_idx]:
        score_a += 15
        details_a["sma200"] = 15
    if ichimoku_df is not None:
        span_a = ichimoku_df['ISA_9'].iloc[curr_idx]
        span_b = ichimoku_df['ISB_26'].iloc[curr_idx]
        if pd.notna(span_a) and pd.notna(span_b) and close.iloc[curr_idx] > max(span_a, span_b):
            score_a += 10
            details_a["ichimoku"] = 10
    if adx_df is not None:
        adx_curr = adx_df.iloc[curr_idx, 0]
        adx_prev = adx_df.iloc[prev_idx, 0]
        if adx_curr >= 25 and adx_curr > adx_prev:
            score_a += 10
            details_a["adx_trend"] = 10
    if ema20 is not None and sma75 is not None:
        if ema20.iloc[curr_idx] > sma75.iloc[curr_idx]:
            score_a += 5
            details_a["ema_cross"] = 5
            
    # --- B. 押し目・過熱感レイヤー (40点) ---
    score_b = 0
    details_b = {}
    if rsi is not None:
        rsi_val = rsi.iloc[curr_idx]
        if rsi_val <= 30:
            score_b += 20
            details_b["rsi"] = 20
        elif rsi_val <= 50:
            score_b += 10
            details_b["rsi"] = 10
    if stoch_df is not None:
        # stoch_k
        stoch_k = stoch_df.iloc[curr_idx, 0]
        if stoch_k <= 20: 
            score_b += 10
            details_b["stoch_rsi"] = 10
    if macd_df is not None:
        hist_curr = macd_df.iloc[curr_idx, 1]
        hist_prev = macd_df.iloc[prev_idx, 1]
        if hist_curr < 0 and hist_curr > hist_prev:
            score_b += 10
            details_b["macd_reversal"] = 10
            
    # --- C. 補助・出来高レイヤー (20点) ---
    score_c = 0
    details_c = {}
    if bb_df is not None:
        pb_val = bb_df.iloc[curr_idx, 4]
        if pb_val <= 0.05:
            score_c += 10
            details_c["bollinger_pb"] = 10
    if obv is not None:
        price_curr = close.iloc[curr_idx]
        price_prev = close.iloc[prev_idx]
        obv_curr = obv.iloc[curr_idx]
        obv_prev = obv.iloc[prev_idx]
        if price_curr < price_prev and obv_curr >= obv_prev:
            score_c += 10
            details_c["obv_divergence"] = 10
            
    total_score = score_a + score_b + score_c
    
    return {
        "total_score": total_score,
        "breakdown": {
            "trend": {"score": score_a, "details": details_a},
            "oscillator": {"score": score_b, "details": details_b},
            "trust": {"score": score_c, "details": details_c}
        }
    }

def check_veto_flags(
    df: pd.DataFrame,
    threshold_adx_peak: float = 50.0,
    obv_divergence_multiplier: float = 2.0,
    threshold_sma200_slope: float = 0.0
) -> Dict[str, str]:
    """
    トレードを控えるべき危険信号 (VETO) を検知します。
    """
    if df is None or len(df) < 5:
        return {}

    # カラム名の正規化 (先頭大文字)
    df_calc = df.copy()
    df_calc.columns = [c.capitalize() for c in df_calc.columns]

    vetos = {}
    close = df_calc['Close']
    high = df_calc['High']
    low = df_calc['Low']
    volume = df_calc['Volume']
    
    # 指標の計算
    sma200 = ta.sma(close, length=200)
    adx_df = ta.adx(high, low, close)
    obv = ta.obv(close, volume)
    
    curr = -1
    prev = -2

    # --- VETO ①：SMA200の「急角度な下向き」 ---
    if sma200 is not None and not sma200.empty:
        s200_curr = sma200.iloc[curr]
        s200_prev = sma200.iloc[prev]
        price_curr = close.iloc[curr]
        
        # 条件: 価格がSMA200より下 かつ SMA200自体が設定した閾値以上の割合で下落
        if pd.notna(s200_curr) and pd.notna(s200_prev) and s200_prev != 0:
            s200_slope = (s200_curr - s200_prev) / s200_prev
            if price_curr < s200_curr and s200_slope < -threshold_sma200_slope:
                vetos["SMA200の下落トレンド"] = (
                    "長期的な下落トレンドが支配しており、価格がSMA200を下回るだけでなく移動平均線自体も下向きです。"
                    "この下げは押し目ではなく、底なしの売り圧力が続いている可能性が高いため、取引を控えるべき状態です。"
                )

    # --- VETO ②：ADXの「超高値（50以上）」からの反落 ---
    if adx_df is not None and not adx_df.empty:
        adx_curr = adx_df.iloc[curr, 0]
        adx_prev = adx_df.iloc[prev, 0]
        
        # 条件: 前日がしきい値(50)以上 かつ 当日が前日より下落（ピークアウト）
        if adx_prev >= threshold_adx_peak and adx_curr < adx_prev:
            vetos["ADXお祭り終了"] = (
                f"トレンドの強さを示すADXが{threshold_adx_peak}以上の過熱圏から反落しました。"
                "これはトレンドのエネルギーが枯渇し、崩壊や転換に向かうサインである可能性が高いため、逆張りを避けるべき局面です。"
            )

    # --- VETO ③：OBVの「ダイバージェンス（急落）」 ---
    if obv is not None and not obv.empty:
        price_curr = close.iloc[curr]
        price_prev = close.iloc[prev]
        obv_curr = obv.iloc[curr]
        obv_prev = obv.iloc[prev]
        
        # 下落率の計算 (ゼロ除算回避)
        if price_prev != 0 and obv_prev != 0:
            price_change_pct = (price_curr - price_prev) / price_prev
            obv_change_pct = (obv_curr - obv_prev) / abs(obv_prev)
            
            # 条件: 価格が下落しており、かつOBVがそれ以上の倍率で急落している
            if price_change_pct < 0 and obv_change_pct < (price_change_pct * obv_divergence_multiplier):
                vetos["OBVの大口離脱"] = (
                    "価格の下落以上に出来高（OBV）が急落しており、大口投資家の離脱が疑われます。"
                    "買い支えのエネルギーが不足しているため、一時的な反発があってもすぐに叩き落とされる危険性が高いです。"
                )
                
    return vetos

def analyze_market(df: pd.DataFrame) -> Dict[str, Any]:
    """
    DataFrameを受け取り、テクニカルスコアとVETOフラグ、マーケットスナップショットをまとめて返却します。
    """
    if df is None or df.empty:
        return get_error_response("No data provided", "データが空であるか、取得できませんでした。")

    if len(df) < MIN_ROWS_REQUIRED:
        return get_error_response(
            "Insufficient data rows",
            f"必要な{MIN_ROWS_REQUIRED}行のデータが取得できませんでした。(取得行数: {len(df)})"
        )

    # 大文字・小文字両対応
    df_normalized = df.copy()
    df_normalized.columns = [c.capitalize() for c in df_normalized.columns]

    # スコア計算
    score_result = calculate_technical_score(df_normalized)
    
    # VETOチェック
    vetos = check_veto_flags(df_normalized)

    # 生の主要指標を取得 (output用)
    raw_indicators = calculate_indicators(df_normalized)
    
    return {
        "technical_score": score_result.get("total_score", 0),
        "score_breakdown": score_result.get("breakdown", {}),
        "is_veto_active": len(vetos) > 0,
        "veto_reasons": vetos,
        "raw_indicators": raw_indicators,
        "market_snapshot": {
            "last_close": round(df_normalized['Close'].iloc[-1], 4) if 'Close' in df_normalized.columns else 0.0,
            "data_period": f"{len(df_normalized)} days"
        }
    }

if __name__ == "__main__":
    # テスト用ダミーデータ生成
    import numpy as np
    data = {
        'Open': np.random.randn(300).cumsum() + 100,
        'High': np.random.randn(300).cumsum() + 105,
        'Low': np.random.randn(300).cumsum() + 95,
        'Close': np.random.randn(300).cumsum() + 100,
        'Volume': np.random.randint(100, 1000, 300)
    }
    test_df = pd.DataFrame(data)
    
    # 指標の計算
    ind = calculate_indicators(test_df)
    # スコアの計算
    scr = calculate_technical_score(test_df)
    # 統合分析
    ana = analyze_market(test_df)
    
    print("--- Indicators Output (Unified) ---")
    for k, v in ind.items():
        print(f"{k:15}: {v:>12.4f}")
        
    print("\n--- Technical Score (Unified) ---")
    print(f"Total Score: {scr['total_score']} / 100")
    for layer, d in scr['breakdown'].items():
        print(f"- {layer.capitalize()}: {d['score']} pts")

    print("\n--- Analyze Market Result ---")
    print(f"VETO Active: {ana['is_veto_active']}")
    if ana['is_veto_active']:
        for k, v in ana['veto_reasons'].items():
            print(f"  VETO: {k}")
