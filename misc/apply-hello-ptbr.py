#!/usr/bin/env python3
"""Replace rustdesk-api admin hello.html (Mandarin default) with pt-BR."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HELLO_CANDIDATES = (HERE / "hello.html", HERE / "i18n" / "hello.html")


def main() -> int:
    src = next((p for p in HELLO_CANDIDATES if p.is_file()), None)
    if src is None:
        print("missing hello.html", file=sys.stderr)
        return 1
    body = src.read_text(encoding="utf-8")
    roots = [Path(p) for p in sys.argv[1:] or ("/opt/rustdesk-api", "/opt/rustdesk", "/tmp/infra-monitor-run/api")]
    n = 0
    js_n = 0
    old_js = "this.replaceAdminTitle(e.data.title),this.setting.hello=e.data.hello"
    new_js = (
        'this.replaceAdminTitle(e.data.title),this.setting.hello=(e.data.hello||"")'
        '.replace(/你好/g,"Olá").replace(/欢迎使用/g,"bem-vindo ao")'
        '.replace(/RustDesk API/g,"Infra-Monitor")'
    )
    for root in roots:
        if not root.exists():
            continue
        for dest in root.rglob("hello.html"):
            dest.write_text(body, encoding="utf-8")
            print(f"hello {dest}")
            n += 1
        for js in root.rglob("*.js"):
            try:
                if js.stat().st_size > 12_000_000:
                    continue
                text = js.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if old_js not in text:
                continue
            js.write_text(text.replace(old_js, new_js, 1), encoding="utf-8")
            print(f"hello-js {js}")
            js_n += 1
    print(f"hello.html updated ({n}), web bundle(s) {js_n}")
    return 0 if n or js_n else 1


if __name__ == "__main__":
    raise SystemExit(main())
