import sys
import os
import streamlit as st
from src.ui.webclip_config import apply_webclip_config

# ─── パス設定（ProjectRoot を sys.path に追加） ───
_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

# 親ディレクトリも追加（パッケージ競合回避用）
_PARENT_DIR = os.path.dirname(_ROOT_DIR)
if _PARENT_DIR not in sys.path:
    sys.path.append(_PARENT_DIR)


# ─── UI設定の永続化（ファイルベース） ───────────────────────
_PREF_FILE = os.path.join(_ROOT_DIR, ".ui_preference")

def _load_ui_preference():
    """保存済みのUI設定を読み込む。未保存 or 無効なら None。"""
    try:
        if os.path.exists(_PREF_FILE):
            with open(_PREF_FILE, "r") as f:
                key = f.read().strip()
            return key
    except Exception:
        pass
    return None

def _save_ui_preference(key):
    """UI設定をファイルに永続保存する。"""
    try:
        with open(_PREF_FILE, "w") as f:
            f.write(key)
    except Exception:
        pass


# ─── UI レジストリ ───────────────────────────────────────────
# 新しいUI skin を追加するときはここに1行追加
UI_REGISTRY = [
    {
        "key":    "classic",
        "name":   "cryptoSIGNAL",
        "icon":   "📡",
        "desc":   "テクニカル指標の統合スコアリングをシンプルに見せる classic skin。",
        "module": "src.ui.cls_skin",
    },
]

_UI_MAP = {u["key"]: u for u in UI_REGISTRY}

# ─── セレクター画面のスタイル ────────────────────────────────
_SELECTOR_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=IBM+Plex+Mono:wght@500;600&family=Outfit:wght@600;700;800&display=swap');

:root {
    --bg:      #0d0d0d;
    --surface: #141414;
    --border:  #2a2a2a;
    --accent:  #4f8ef7;
    --text:    #ffffff;
    --text-2:  #888888;
}

.sel-header {
    font-family: 'Orbitron', sans-serif;
    font-size: 2.2rem; font-weight: 900;
    color: var(--text); letter-spacing: 4px;
    margin-bottom: 0.5rem; text-align: center;
}
.sel-sub {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem; letter-spacing: 2px;
    color: var(--accent); text-align: center;
    margin-bottom: 2.5rem;
}
.sel-footer {
    margin-top: 3rem; text-align: center;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem; color: #444; letter-spacing: 1px;
}

/* Button Styling (Tiles) */
div[data-testid="stButton"] > button {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-left: 4px solid var(--border) !important;
    border-radius: 4px !important;
    padding: 1.5rem !important;
    text-align: left !important;
    height: auto !important;
    white-space: pre-wrap !important;
    transition: all 0.2s !important;
}

div[data-testid="stButton"] > button:hover {
    background: rgba(79,142,247,0.08) !important;
    border-left-color: var(--accent) !important;
    color: var(--accent) !important;
}
</style>
"""

def _load_ui_module(module_path: str):
    """動的インポート。"""
    import importlib
    try:
        # すでに sys.modules にある場合、KeyError やリロード不備を防ぐために強制削除
        if module_path in sys.modules:
            del sys.modules[module_path]
        return importlib.import_module(module_path)
    except Exception as e:
        st.error(f"UIモジュールの読み込みに失敗しました: `{module_path}`\n\n{e}")
        return None

def render_selector():
    """UI選択画面を描画。"""
    st.markdown(_SELECTOR_CSS, unsafe_allow_html=True)
    st.markdown('<div class="sel-header">▶ SELECT SKIN ◀</div>', unsafe_allow_html=True)
    st.markdown('<div class="sel-sub">cryptoSIGNAL — DYNAMIC UI SELECTOR</div>', unsafe_allow_html=True)

    selected_key = None
    for ui in UI_REGISTRY:
        label = f"{ui['icon']}  {ui['name']}\n{ui['desc']}"
        if st.button(label, key=f"sel_{ui['key']}", use_container_width=True):
            selected_key = ui["key"]

    st.markdown('<div class="sel-footer">■ INTERNAL MODULES: src.ui.* ■</div>', unsafe_allow_html=True)
    return selected_key

def main():
    apply_webclip_config(_ROOT_DIR)

    if "ui_key" not in st.session_state:
        saved = _load_ui_preference()
        st.session_state["ui_key"] = saved if (saved and saved in _UI_MAP) else None

    try:
        url_ui = st.query_params.get("ui", None)
        if url_ui and url_ui in _UI_MAP:
            st.session_state["ui_key"] = url_ui
    except Exception:
        pass

    current_key = st.session_state.get("ui_key")

    if current_key is None:
        chosen = render_selector()
        if chosen:
            st.session_state["ui_key"] = chosen
            _save_ui_preference(chosen)
            st.rerun()
        return

    ui_entry = _UI_MAP.get(current_key)
    mod = _load_ui_module(ui_entry["module"])
    if mod is None:
        if st.button("← セレクターに戻る"):
            st.session_state["ui_key"] = None
            st.rerun()
        return

    # サイドバーにUI切り替え
    with st.sidebar:
        st.markdown(f"**Skin: {ui_entry['icon']} {ui_entry['name']}**")
        st.markdown("---")
        if st.button("🏠 スキン選択に戻る", use_container_width=True):
            st.session_state["ui_key"] = None
            _save_ui_preference("")
            st.rerun()

    # スキンの実行
    mod.run()

if __name__ == "__main__":
    main()
