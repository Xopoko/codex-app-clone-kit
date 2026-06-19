#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


SENSITIVE_NAME_RE = re.compile(r"(API_KEY|TOKEN|SECRET|PASSWORD|AUTHORIZATION|BEARER)", re.I)


def strip_sensitive_env_tables(text: str) -> str:
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^\s*\[(mcp_servers\.[^\]]+\.env)\]\s*$", line)
        if not m:
            out.append(line)
            i += 1
            continue

        block = [line]
        i += 1
        while i < len(lines) and not re.match(r"^\s*\[", lines[i]):
            block.append(lines[i])
            i += 1

        if any(SENSITIVE_NAME_RE.search(item) for item in block):
            out.append(f"# Removed [{m.group(1)}] for Codex Work: contained personal inline credentials.\n")
        else:
            out.extend(block)

    return "".join(out)


def main() -> int:
    if len(sys.argv) != 5:
        print("usage: sanitize-config.py <src> <dst> <personal-home> <work-home>", file=sys.stderr)
        return 2

    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    personal_home = sys.argv[3]
    work_home = sys.argv[4]

    text = src.read_text(encoding="utf-8")
    text = strip_sensitive_env_tables(text)
    text = text.replace("/Applications/Codex.app", "/Applications/Codex Work.app")
    text = text.replace("/Applications/Codex OpenRouter Models.app", "/Applications/Codex Work.app")
    text = text.replace("/Users/max/.codex-openrouter", work_home)
    text = text.replace(personal_home, work_home)

    header = (
        "# Codex Work profile config.\n"
        "# Generated from /Users/max/.codex/config.toml with personal auth/session data excluded.\n"
        "# Login with the work ChatGPT/Codex account from /Applications/Codex Work.app.\n\n"
    )
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(header + text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

