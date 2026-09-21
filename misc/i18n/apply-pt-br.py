#!/usr/bin/env python3
"""Register Português (Brasil) in rustdesk-api WebUI language menu + i18n files."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

LANG_KEY = "pt-BR"
LANG_ALIASES = ("pt-BR", "pt-br", "pt_BR", "pt")
LANG_NAME = "Português (Brasil)"


def _balanced_object(src: str, start: int) -> int | None:
    if start >= len(src) or src[start] != "{":
        return None
    depth = 0
    i = start
    in_str = False
    quote = ""
    escape = False
    while i < len(src):
        ch = src[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                in_str = False
        else:
            if ch in ("'", '"'):
                in_str = True
                quote = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    return None


def _insert_after_object(js: str, header_re: str, payload: str) -> str:
    m = re.search(header_re, js)
    if not m:
        return js
    start = m.start("obj") if "obj" in m.re.groupindex else m.end() - 1
    end = _balanced_object(js, start)
    if end is None:
        return js
    return js[: end + 1] + "," + payload + js[end + 1 :]


def _insert_lang_menu(js: str) -> str:
    if re.search(r'["\']pt-BR["\']\s*:\s*\{\s*name\s*:', js):
        return js

    en = re.search(
        r"""["']en["']\s*:\s*\{\s*name\s*:\s*["']English["']\s*,\s*value\s*:\s*([^,]+)\s*,""",
        js,
    )
    value_ref = en.group(1) if en else "en"
    entry = (
        f'{json.dumps(LANG_KEY)}:{{name:{json.dumps(LANG_NAME, ensure_ascii=False)},'
        f'value:{value_ref},sideBarWidth:"230px"}}'
    )
    updated = _insert_after_object(js, r"""["']zh-TW["']\s*:\s*(?P<obj>\{)\s*name\s*:""", entry)
    if updated != js:
        return updated
    return _insert_after_object(js, r"""["']en["']\s*:\s*(?P<obj>\{)\s*name\s*:\s*["']English["']""", entry)


def _insert_translations(js: str, messages: dict) -> str:
    if re.search(r'["\']pt-BR["\']\s*:\s*\{\s*["\']?Login["\']?\s*:', js):
        return js
    payload = json.dumps(LANG_KEY) + ":" + json.dumps(messages, ensure_ascii=False, separators=(",", ":"))
    updated = _insert_after_object(js, r"""["']zh-TW["']\s*:\s*(?P<obj>\{)\s*Login\s*:""", payload)
    if updated != js:
        return updated
    return _insert_after_object(js, r"""["']es["']\s*:\s*(?P<obj>\{)\s*Login\s*:""", payload)


def patch_js(path: Path, messages: dict) -> bool:
    original = path.read_text(encoding="utf-8", errors="replace")
    updated = _insert_translations(_insert_lang_menu(original), messages)
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def copy_backend(toml_src: Path, roots: list[Path]) -> None:
    for root in roots:
        for dest_dir in root.rglob("i18n"):
            if not dest_dir.is_dir():
                continue
            for name in ("pt_BR.toml", "pt-BR.toml"):
                dest = dest_dir / name
                dest.write_text(toml_src.read_text(encoding="utf-8"), encoding="utf-8")


def set_config_lang(roots: list[Path]) -> None:
    for root in roots:
        for cfg in root.rglob("config.yaml"):
            text = cfg.read_text(encoding="utf-8", errors="replace")
            new, n = re.subn(r'(?m)^lang:\s*["\']?[\w.-]+["\']?', 'lang: "pt-BR"', text, count=1)
            if n:
                cfg.write_text(new, encoding="utf-8")


def main() -> int:
    here = Path(__file__).resolve().parent
    json_path = here / "pt_BR.json"
    toml_path = here / "pt_BR.toml"
    if not json_path.is_file():
        print("missing pt_BR.json", file=sys.stderr)
        return 1
    messages = json.loads(json_path.read_text(encoding="utf-8"))

    roots = [Path(p) for p in sys.argv[1:] or ("/opt/rustdesk-api", "/opt/rustdesk")]
    roots = [p for p in roots if p.exists()]
    if not roots:
        print("rustdesk-api install path not found", file=sys.stderr)
        return 1

    copy_backend(toml_path, roots)
    set_config_lang(roots)

    patched = 0
    for root in roots:
        for js in root.rglob("*.js"):
            try:
                if js.stat().st_size > 12_000_000:
                    continue
                text = js.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "sideBarWidth" not in text or "English" not in text:
                continue
            if patch_js(js, messages):
                patched += 1
                print(f"patched {js}")
    print(f"pt-BR ready ({patched} web bundle(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
