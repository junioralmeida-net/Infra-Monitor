#!/usr/bin/env python3
"""Replace rustdesk-api admin hello.html (Mandarin default) with pt-BR."""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HELLO_CANDIDATES = (HERE / "hello.html", HERE / "i18n" / "hello.html")
BRAND_TITLE = "NETWORK Informática  ·  Infra-Monitor"
JS_TITLE = f'title:"{BRAND_TITLE}"'
OLD_JS_TITLES = (
    'title:"Rustdesk API Admin"',
    'title:"RustDesk API Admin"',
    'title:"Infra-Monitor"',
    JS_TITLE,
)
OLD_PLAIN_TITLES = (
    "Rustdesk API Admin",
    "RustDesk API Admin",
    BRAND_TITLE,
)


def _rebrand_text(text: str) -> str:
    for old in OLD_JS_TITLES:
        if old in text:
            text = text.replace(old, JS_TITLE)
    for old in OLD_PLAIN_TITLES:
        if old in text:
            text = text.replace(old, BRAND_TITLE)
    text = text.replace("<title>Infra-Monitor</title>", f"<title>{BRAND_TITLE}</title>")
    return text


def _set_config_title(cfg: Path) -> bool:
    text = cfg.read_text(encoding="utf-8", errors="replace")
    new, n = re.subn(
        r'(?m)^(\s*title:\s*)(["\']?)(Rustdesk API Admin|RustDesk API Admin|Infra-Monitor|NETWORK Informática  ·  Infra-Monitor)\2',
        rf'\1"{BRAND_TITLE}"',
        text,
        count=1,
    )
    if not n or new == text:
        return False
    cfg.unlink(missing_ok=True)
    cfg.write_text(new, encoding="utf-8")
    return True


def main() -> int:
    src = next((p for p in HELLO_CANDIDATES if p.is_file()), None)
    if src is None:
        print("missing hello.html", file=sys.stderr)
        return 1
    body = src.read_text(encoding="utf-8")
    roots = [Path(p) for p in sys.argv[1:] or ("/opt/rustdesk-api", "/opt/rustdesk", "/tmp/infra-monitor-run")]
    n = 0
    js_n = 0
    old_js = "this.replaceAdminTitle(e.data.title),this.setting.hello=e.data.hello"
    new_js = (
        'this.replaceAdminTitle(e.data.title),this.setting.hello=(e.data.hello||"")'
        '.replace(/👏+/g,"").replace(/你好/g,"Olá").replace(/欢迎使用/g,"bem-vindo ao")'
        '.replace(/RustDesk API/g,"Infra-Monitor")'
    )
    for root in roots:
        if not root.exists():
            continue
        for dest in root.rglob("hello.html"):
            dest.unlink(missing_ok=True)
            dest.write_text(body, encoding="utf-8")
            print(f"hello {dest}")
            n += 1
        for cfg in root.rglob("config.yaml"):
            if _set_config_title(cfg):
                print(f"title-config {cfg}")
        for html in root.rglob("index.html"):
            if "admin" not in str(html):
                continue
            ht = html.read_text(encoding="utf-8", errors="replace")
            nt = _rebrand_text(ht)
            if nt != ht:
                html.unlink(missing_ok=True)
                html.write_text(nt, encoding="utf-8")
                print(f"title {html}")
        for js in root.rglob("*.js"):
            try:
                if js.stat().st_size > 12_000_000:
                    continue
                text = js.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            updated = text
            if old_js in updated:
                updated = updated.replace(old_js, new_js, 1)
            branded = _rebrand_text(updated)
            if branded == text:
                continue
            js.unlink(missing_ok=True)
            js.write_text(branded, encoding="utf-8")
            print(f"hello-js {js}")
            js_n += 1
    print(f"hello.html updated ({n}), web bundle(s) {js_n}")
    return 0 if n or js_n else 1


if __name__ == "__main__":
    raise SystemExit(main())
