#!/usr/bin/env python3
"""Replace rustdesk-api WebUI logos with NETWORK LOGO4 on brand orange.

Original rustdesk-api mark is 128x128, shown at 30px in the header and 80px
on the login card. The composed asset (logo-webui.png) matches that size.
"""
from __future__ import annotations

import base64
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOGO_CANDIDATES = (
    HERE / "images" / "logo-webui.png",
    HERE / "images" / "LOGO4.png",
    HERE.parent / "PASTA_BASE" / "LOGO4.png",
    HERE / "images" / "logo-network-n.png",
)

_LE = re.compile(r'const le="data:image/[^"]+"')
_HEADER_LOGO = re.compile(
    r"\.header-logo \.logo\[data-v-[a-f0-9]+\]\{display:block;[^}]*\}"
)
_LOGIN_LOGO = re.compile(
    r"\.login-logo\[data-v-[a-f0-9]+\]\{[^}]*\}"
)
# Match the upstream rustdesk-api sizes (header 30px, login 80px).
_HEADER_RULE = (
    ".header-logo .logo[data-v-{vid}]{{display:block;width:30px;height:30px;"
    "object-fit:contain;filter:none}}"
)
_LOGIN_RULE = (
    ".login-logo[data-v-{vid}]{{width:80px;height:80px;margin:0 auto 20px;"
    "display:block;object-fit:contain;filter:none}}"
)


def _find_logo() -> Path:
    for path in LOGO_CANDIDATES:
        if path.is_file():
            return path
    raise FileNotFoundError("NETWORK WebUI logo not found")


def _png_data_uri(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def _vid(match: re.Match[str]) -> str:
    found = re.search(r"data-v-([a-f0-9]+)", match.group(0))
    return found.group(1) if found else "0"


def _patch_js(root: Path, uri: str) -> int:
    n = 0
    for js in root.rglob("*.js"):
        try:
            if js.stat().st_size > 12_000_000:
                continue
            text = js.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not _LE.search(text):
            continue
        updated, count = _LE.subn(f'const le="{uri}"', text, count=1)
        if count:
            js.write_text(updated, encoding="utf-8")
            print(f"logo-js {js}")
            n += 1
    return n


def _patch_css(root: Path) -> int:
    n = 0
    for css in root.rglob("*.css"):
        try:
            text = css.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        updated = text
        updated = _HEADER_LOGO.sub(
            lambda m: _HEADER_RULE.format(vid=_vid(m)), updated
        )
        updated = _LOGIN_LOGO.sub(
            lambda m: _LOGIN_RULE.format(vid=_vid(m)), updated
        )
        if updated != text:
            css.write_text(updated, encoding="utf-8")
            print(f"logo-css {css}")
            n += 1
    return n


def main() -> int:
    logo = _find_logo()
    uri = _png_data_uri(logo)
    roots = [
        Path(p)
        for p in sys.argv[1:]
        or ("/opt/rustdesk-api", "/opt/rustdesk", "/var/lib/rustdesk-api")
    ]
    js_n = css_n = 0
    for root in roots:
        if not root.exists():
            continue
        js_n += _patch_js(root, uri)
        css_n += _patch_css(root)
    print(f"LOGO4 (orange {logo.name}) applied (js {js_n}, css {css_n})")
    return 0 if js_n or css_n else 1


if __name__ == "__main__":
    raise SystemExit(main())
