#!/usr/bin/env python
from __future__ import annotations

import sys
from pathlib import Path

BAD_SEQUENCE = chr(92) + '"'  # backslash + double quote


def should_skip(path: Path) -> bool:
    parts = {p.lower() for p in path.parts}
    return any(p in {'.git', '.venv', 'venv', 'dist', 'build', '__pycache__'} for p in parts)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    failures: list[str] = []
    for py_file in root.rglob("*.py"):
        if should_skip(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(content.splitlines(), start=1):
            if BAD_SEQUENCE in line:
                failures.append(f"{py_file}:{lineno}: contains backslash+quote sequence")
    if failures:
        print("Bad escape sequences detected:\n" + "\n".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
