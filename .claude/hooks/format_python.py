#!/usr/bin/env python3
"""PostToolUse hook: run `ruff format` on a Python file Claude just edited.

Reads the hook payload on stdin. Silent no-op when the file is not Python or ruff is missing,
so it never blocks a session.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def find_ruff(project: Path) -> str | None:
    candidates = [project / ".venv" / "bin" / "ruff", project / ".venv" / "Scripts" / "ruff.exe"]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return shutil.which("ruff")


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    path = payload.get("tool_input", {}).get("file_path", "")
    if not path.endswith(".py"):
        return
    ruff = find_ruff(Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")))
    if ruff is None:
        return
    subprocess.run([ruff, "format", "--quiet", path], check=False)


if __name__ == "__main__":
    main()
