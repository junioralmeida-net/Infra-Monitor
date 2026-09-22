#!/usr/bin/env python3
"""Register Português (Brasil) in rustdesk-api WebUI language menu + i18n files."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

LANG_KEY = "pt-BR"
LANG_ALIASES = ("pt-BR", "pt-br", "pt_BR", "pt")
LANG_NAME = "Português (Brasil)"

DEFAULT_ROOTS = (
    "/var/lib/rustdesk-api",
    "/opt/rustdesk-api",
    "/opt/rustdesk",
    "/usr/share/rustdesk-api",
)


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


def _unique_existing(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for raw in paths:
        try:
            path = raw.resolve() if raw.exists() else raw
        except OSError:
            continue
        if not path.exists() or path in seen:
            continue
        seen.add(path)
        out.append(path)
    return out


def discover_roots(argv: list[str]) -> list[Path]:
    candidates = [Path(p) for p in argv]
    candidates.extend(Path(p) for p in DEFAULT_ROOTS)
    try:
        proc = subprocess.run(
            ["systemctl", "show", "-p", "WorkingDirectory", "--value", "rustdesk-api.service"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        wd = (proc.stdout or "").strip()
        if wd and wd not in {"", "/", "n/a"}:
            candidates.append(Path(wd))
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        proc = subprocess.run(
            ["dpkg", "-L", "rustdesk-api-server"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        for line in proc.stdout.splitlines():
            path = Path(line)
            if path.name == "resources" and path.is_dir():
                candidates.append(path.parent)
            elif path.name == "admin" and path.is_dir():
                parent = path.parent
                candidates.append(parent.parent if parent.name == "resources" else parent)
    except (OSError, subprocess.SubprocessError):
        pass
    return _unique_existing(candidates)


def main() -> int:
    here = Path(__file__).resolve().parent
    json_path = here / "pt_BR.json"
    toml_path = here / "pt_BR.toml"
    if not json_path.is_file():
        print("missing pt_BR.json", file=sys.stderr)
        return 1
    messages = json.loads(json_path.read_text(encoding="utf-8"))

    roots = discover_roots(sys.argv[1:])
    if not roots:
        print("rustdesk-api install path not found; skipping pt-BR WebUI patch", file=sys.stderr)
        return 0

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
