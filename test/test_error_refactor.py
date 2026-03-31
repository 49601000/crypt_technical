import pandas as pd
import numpy as np
from crypt_analytics import analyze_market
from crypt_judgement import evaluate_investment
import json

def test_insufficient_data():
    print("=== Testing Insufficient Data (< 200 rows) ===")
    # 50行だけのダミーデータを作成
    data = {
        'Open': np.random.randn(50).cumsum() + 100,
        'High': np.random.randn(50).cumsum() + 105,
        'Low': np.random.randn(50).cumsum() + 95,
        'Close': np.random.randn(50).cumsum() + 100,
        'Volume': np.random.randint(100, 1000, 50)
    }
    df = pd.DataFrame(data)
    
    # 1. Analytics のテスト
    print("\n[Step 1] analyze_market:")
    analysis_res = analyze_market(df)
    print(json.dumps(analysis_res, indent=2, ensure_ascii=False))
    
    assert analysis_res['status'] == 'error'
    assert 'Insufficient data rows' in analysis_res['message']
    
    # 2. Judgement のテスト
    print("\n[Step 2] evaluate_investment:")
    final_res = evaluate_investment(analysis_res, symbol="TEST-COIN")
    print(json.dumps(final_res, indent=2, ensure_ascii=False))
    
    assert final_res['status'] == 'error'
    assert final_res['symbol'] == 'TEST-COIN'
    assert 'timestamp' in final_res
    assert 'descriptions' in final_res
    
    print("\nVerification Successful!")

if __name__ == "__main__":
    try:
        test_insufficient_data()
    except Exception as e:
        print(f"\nVerification Failed: {e}")
