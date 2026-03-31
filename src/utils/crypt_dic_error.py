from typing import Dict, Any

def get_error_response(message: str, error_detail: str) -> Dict[str, Any]:
    """
    統一されたエラーレスポンス形式を生成して返却します。
    """
    return {
        "status": "error",
        "message": message,
        "level_1_judgement": {"decision": "ERROR", "reason": "Data Fetch Failed"},
        "level_2_score": {"total_score": 0, "breakdown": {}},
        "level_3_indicators": {},
        "descriptions": {"error_detail": error_detail}
    }

# 後方互換性またはテンプレートとしてのデフォルト値
error_response = get_error_response(
    "エラーの内容（例: Insufficient data rows）",
    "必要な200行のデータが取得できませんでした。"
)
