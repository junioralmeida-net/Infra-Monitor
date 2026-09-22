#!/usr/bin/env python3
"""Translate rustdesk-api WebUI language menu labels and replace the globe SVG."""
from __future__ import annotations

import re
import sys
from pathlib import Path

LANG_NAMES = {
    "中文": "Chinês",
    "English": "Inglês",
    "Français": "Francês",
    "한국어": "Coreano",
    "Русский": "Russo",
    "Español": "Espanhol",
    "中文繁体": "Chinês tradicional",
}

_NAME = re.compile(
    r'(name:")(' + "|".join(re.escape(k) for k in LANG_NAMES) + r')(")'
)

_LANG_ICON = re.compile(
    r'h\("i",\{class:"el-icon el-tooltip__trigger",style:\{"font-size":"24px"\}\},'
    r'\[h\("svg",\{preserveAspectRatio:"xMidYMid meet",viewBox:"0 0 24 24",'
    r'width:"1\.2em",height:"1\.2em"\},\[h\("path",\{fill:"currentColor",d:"[^"]+"\}\)\]\)\]\)'
)
_LANG_SVG = re.compile(
    r'h\("svg",\{preserveAspectRatio:"xMidYMid meet",viewBox:"0 0 24 24",'
    r'width:"1\.2em",height:"1\.2em"\},\[h\("path",\{fill:"currentColor",d:"[^"]+"\}\)\]\)'
)
_LANG_IMG = (
    'h("img",{src:"/_admin/static/png/idioma.png",alt:"Idioma",class:"lang-icon",'
    'style:{width:"24px",height:"24px",display:"block","object-fit":"contain"}})'
)
_ICON_SRC = (
    Path(__file__).resolve().parent / "images" / "idioma.png",
    Path(__file__).resolve().parent.parent / "PASTA_BASE" / "idioma.png",
)


def _replace_names(text: str) -> str:
    return _NAME.sub(lambda m: m.group(1) + LANG_NAMES[m.group(2)] + m.group(3), text)


def _replace_icon(text: str) -> str:
    text = text.replace("idioma.jpeg", "idioma.png")
    if "idioma.png" in text and "lang-icon" in text:
        return text
    updated, n = _LANG_ICON.subn(_LANG_IMG, text, count=1)
    if n:
        return updated
    return _LANG_SVG.sub(_LANG_IMG, text, count=1)


def _copy_icon(root: Path) -> bool:
    src = next((p for p in _ICON_SRC if p.is_file()), None)
    if src is None:
        return False
    n = 0
    for admin in root.rglob("index.html"):
        if "admin" not in str(admin):
            continue
        dest_dir = admin.parent / "static" / "png"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / "idioma.png"
        dest.write_bytes(src.read_bytes())
        print(f"lang-icon {dest}")
        n += 1
    return bool(n)


def main() -> int:
    roots = [Path(p) for p in sys.argv[1:] or ("/opt/rustdesk-api", "/opt/rustdesk", "/tmp/infra-monitor-run")]
    n = 0
    for root in roots:
        if not root.exists():
            continue
        _copy_icon(root)
        for js in root.rglob("*.js"):
            try:
                if js.stat().st_size > 12_000_000:
                    continue
                text = js.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "sideBarWidth" not in text and "setting.langs" not in text and "el-tooltip__trigger" not in text:
                continue
            updated = _replace_icon(_replace_names(text))
            if updated == text:
                continue
            js.write_text(updated, encoding="utf-8")
            print(f"langs {js}")
            n += 1
    print(f"language menu translated ({n})")
    return 0 if n else 1


if __name__ == "__main__":
    raise SystemExit(main())
