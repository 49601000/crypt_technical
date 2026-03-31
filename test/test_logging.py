import pandas as pd
from crypt_analytics import calculate_indicators

def test_invalid_data():
    print("--- Test 1: Empty DataFrame ---")
    df_empty = pd.DataFrame()
    res1 = calculate_indicators(df_empty)
    
    print("\n--- Test 2: Missing Columns ---")
    df_missing = pd.DataFrame({'Close': [100.0]})
    res2 = calculate_indicators(df_missing)
    
    print("\n--- Test 3: Valid but short data ---")
    df_valid = pd.DataFrame({
        'Open': [100.0], 'High': [105.0], 'Low': [95.0], 'Close': [100.0], 'Volume': [1000]
    })
    res3 = calculate_indicators(df_valid)

if __name__ == "__main__":
    test_invalid_data()
