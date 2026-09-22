#!/usr/bin/env python3
"""Replace rustdesk-api WebUI logos with NETWORK LOGO4 on brand orange.

Original rustdesk-api mark is 128x128, shown at 30px in the header and 80px
on the login card. The composed asset (logo-webui.png) matches that size.
Also replaces the browser favicon with the Infra-Monitor mark.
"""
from __future__ import annotations

import base64
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOGO_CANDIDATES = (
    HERE / "images" / "logo-webui.png",
    HERE / "images" / "LOGO4.png",
    HERE.parent / "PASTA_BASE" / "LOGO4.png",
    HERE / "images" / "logo-network-n.png",
)
FAVICON_ICO = HERE / "images" / "favicon.ico"
FAVICON_PNG = HERE / "images" / "favicon.png"

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
_ICON_LINK = re.compile(
    r'<link[^>]+rel=["\'](?:shortcut\s+)?icon["\'][^>]*>',
    re.IGNORECASE,
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
            js.unlink(missing_ok=True)
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
            css.unlink(missing_ok=True)
            css.write_text(updated, encoding="utf-8")
            print(f"logo-css {css}")
            n += 1
    return n


def _copy_favicon(dest: Path, src: Path) -> None:
    dest.unlink(missing_ok=True)
    shutil.copy2(src, dest)


def _patch_favicon(root: Path, logo: Path) -> int:
    ico = FAVICON_ICO if FAVICON_ICO.is_file() else None
    png = FAVICON_PNG if FAVICON_PNG.is_file() else logo
    n = 0
    for dest in root.rglob("favicon.ico"):
        src = ico or png
        _copy_favicon(dest, src)
        if png.is_file():
            _copy_favicon(dest.with_name("favicon.png"), png)
        print(f"favicon {dest}")
        n += 1
    for dest in root.rglob("favicon.svg"):
        src = png if png.is_file() else (ico or logo)
        _copy_favicon(dest.with_name("favicon.png"), src)
        print(f"favicon-svg-png {dest.with_name('favicon.png')}")
        n += 1
    for html in root.rglob("index.html"):
        if "admin" not in str(html) and "web" not in str(html):
            continue
        text = html.read_text(encoding="utf-8", errors="replace")
        links = (
            '<link rel="icon" type="image/png" href="./favicon.png" />'
            '<link rel="icon" href="./favicon.ico" />'
        )
        if _ICON_LINK.search(text):
            updated = _ICON_LINK.sub(links, text, count=1)
        elif "</head>" in text:
            updated = text.replace("</head>", f"    {links}\n  </head>", 1)
        else:
            continue
        if "favicon.png" not in updated:
            continue
        # keep a local png next to the html
        if png.is_file():
            _copy_favicon(html.parent / "favicon.png", png)
        if ico and ico.is_file():
            _copy_favicon(html.parent / "favicon.ico", ico)
        if updated != text:
            html.unlink(missing_ok=True)
            html.write_text(updated, encoding="utf-8")
            print(f"favicon-html {html}")
            n += 1
    return n


def main() -> int:
    logo = _find_logo()
    uri = _png_data_uri(logo)
    roots = [
        Path(p)
        for p in sys.argv[1:]
        or ("/opt/rustdesk-api", "/opt/rustdesk", "/var/lib/rustdesk-api", "/tmp/infra-monitor-run")
    ]
    js_n = css_n = ico_n = 0
    for root in roots:
        if not root.exists():
            continue
        js_n += _patch_js(root, uri)
        css_n += _patch_css(root)
        ico_n += _patch_favicon(root, logo)
    print(f"LOGO4 (orange {logo.name}) applied (js {js_n}, css {css_n}, favicon {ico_n})")
    return 0 if js_n or css_n or ico_n else 1


if __name__ == "__main__":
    raise SystemExit(main())
