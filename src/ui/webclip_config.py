"""
iPhone の「ホーム画面に追加」向け Web Clip 設定を config/webclip.toml から適用する。
"""
from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path
from typing import Any, Dict

import streamlit as st
import streamlit.components.v1 as components

try:
    import tomllib  # Python 3.11+
except Exception:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]


def _load_webclip_config(root_dir: str) -> Dict[str, Any]:
    """config/webclip.toml を読み込んで webclip セクションを返す。"""
    if tomllib is None:
        return {}

    cfg_path = Path(root_dir) / "config" / "webclip.toml"
    if not cfg_path.exists():
        return {}

    try:
        with cfg_path.open("rb") as f:
            data = tomllib.load(f)
        section = data.get("webclip", {})
        return section if isinstance(section, dict) else {}
    except Exception as e:
        print(f"webclip config load warning: {e}")
        return {}


def _icon_href_from_config(root_dir: str, cfg: Dict[str, Any]) -> str:
    """icon_url か icon_path から <link rel='apple-touch-icon'> 用の href を作る。"""
    icon_url = str(cfg.get("icon_url", "")).strip()
    if icon_url:
        return icon_url

    icon_path_raw = str(cfg.get("icon_path", "")).strip()
    if not icon_path_raw:
        return ""

    icon_path = Path(icon_path_raw)
    if not icon_path.is_absolute():
        icon_path = Path(root_dir) / icon_path
    icon_path = icon_path.resolve()

    if not icon_path.exists() or not icon_path.is_file():
        print(f"webclip icon not found: {icon_path}")
        return ""

    try:
        binary = icon_path.read_bytes()
        mime = mimetypes.guess_type(icon_path.name)[0] or "image/png"
        b64 = base64.b64encode(binary).decode("ascii")
        return f"data:{mime};base64,{b64}"
    except Exception as e:
        print(f"webclip icon load warning: {e}")
        return ""


def apply_webclip_config(root_dir: str) -> None:
    """
    Safari / iOS 向けメタタグとアイコンを head に注入する。
    Streamlit の標準APIだけでは apple-touch-icon を直接指定しづらいため、
    小さなJSで parent document の head を更新する。
    """
    cfg = _load_webclip_config(root_dir)
    if not cfg:
        return

    if not bool(cfg.get("enabled", False)):
        return

    icon_href = _icon_href_from_config(root_dir, cfg)
    if not icon_href:
        return

    payload = {
        "app_title": str(cfg.get("app_title", "cryptoSIGNAL")),
        "icon_href": icon_href,
        "icon_size": str(cfg.get("icon_size", "180x180")),
        "theme_color": str(cfg.get("theme_color", "#0f1117")),
        "background_color": str(cfg.get("background_color", "#0f1117")),
    }
    payload_json = json.dumps(payload, ensure_ascii=False)

    components.html(
        f"""
<script>
(function() {{
  const cfg = {payload_json};
  const doc = window.parent && window.parent.document ? window.parent.document : document;
  const head = doc.head;
  if (!head) return;

  function upsertMeta(name, content) {{
    if (!content) return;
    let el = head.querySelector(`meta[name="${{name}}"]`);
    if (!el) {{
      el = doc.createElement("meta");
      el.setAttribute("name", name);
      head.appendChild(el);
    }}
    el.setAttribute("content", content);
  }}

  function upsertLink(rel, href, sizes) {{
    if (!href) return;
    let el = head.querySelector(`link[rel="${{rel}}"]`);
    if (!el) {{
      el = doc.createElement("link");
      el.setAttribute("rel", rel);
      head.appendChild(el);
    }}
    el.setAttribute("href", href);
    if (sizes) {{
      el.setAttribute("sizes", sizes);
    }}
  }}

  upsertMeta("apple-mobile-web-app-capable", "yes");
  upsertMeta("apple-mobile-web-app-title", cfg.app_title);
  upsertMeta("theme-color", cfg.theme_color);
  upsertMeta("msapplication-TileColor", cfg.background_color);

  upsertLink("apple-touch-icon", cfg.icon_href, cfg.icon_size);
  upsertLink("icon", cfg.icon_href, cfg.icon_size);
  upsertLink("shortcut icon", cfg.icon_href, cfg.icon_size);
}})();
</script>
""",
        height=0,
        width=0,
    )
