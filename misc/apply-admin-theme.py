#!/usr/bin/env python3
"""Inject Infra-Guardian / NETWORK theme into rustdesk-api admin WebUI."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
THEME = HERE / "images" / "admin-theme.css"
TOKENS = HERE / "images" / "brand-tokens.css"
LINK = '<link rel="stylesheet" href="./static/css/admin-theme.css" />'


def _inject_html(html: Path) -> bool:
    text = html.read_text(encoding="utf-8", errors="replace")
    if "admin-theme.css" in text:
        return False
    marker = "</head>"
    if marker not in text:
        return False
    html.write_text(text.replace(marker, f"    {LINK}\n  {marker}", 1), encoding="utf-8")
    return True


def main() -> int:
    if not THEME.is_file():
        print("missing admin-theme.css", file=sys.stderr)
        return 1
    roots = [
        Path(p)
        for p in sys.argv[1:]
        or ("/opt/rustdesk-api", "/opt/rustdesk", "/tmp/infra-monitor-run/api")
    ]
    n = 0
    for root in roots:
        if not root.exists():
            continue
        for admin in root.rglob("index.html"):
            if "admin" not in str(admin):
                continue
            css_dir = admin.parent / "static" / "css"
            css_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(THEME, css_dir / "admin-theme.css")
            if TOKENS.is_file():
                shutil.copy2(TOKENS, css_dir / "brand-tokens.css")
            if _inject_html(admin):
                print(f"theme-html {admin}")
            print(f"theme-css {css_dir / 'admin-theme.css'}")
            n += 1
    print(f"admin theme applied ({n})")
    return 0 if n else 1


if __name__ == "__main__":
    raise SystemExit(main())
