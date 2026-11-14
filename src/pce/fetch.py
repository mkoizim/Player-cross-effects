"""Fetch pinned raw inputs: Retrosheet (Chadwick Bureau mirror) and the Chadwick tools.

Idempotent. Refuses to proceed if an existing checkout is not at the pinned SHA.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from .config import CFG, CHADWICK, CHADWICK_SRC, RAW, RETROSHEET


def _run(cmd, cwd=None):
    subprocess.run(cmd, cwd=cwd, check=True)


def _head(path: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=path, check=True, capture_output=True, text=True
    ).stdout.strip()


def _checkout(url: str, sha: str, dest: Path) -> None:
    if (dest / ".git").exists():
        have = _head(dest)
        if have != sha:
            raise SystemExit(f"{dest} is at {have}, config pins {sha}. Remove it and re-run.")
        print(f"ok  {dest.name} @ {sha[:10]}")
        return
    dest.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q"], cwd=dest)
    _run(["git", "remote", "add", "origin", url], cwd=dest)
    _run(["git", "fetch", "-q", "--depth", "1", "origin", sha], cwd=dest)
    _run(["git", "checkout", "-q", "FETCH_HEAD"], cwd=dest)
    print(f"got {dest.name} @ {sha[:10]}")


def build_chadwick() -> None:
    if (CHADWICK / "bin" / "cwevent").exists():
        print("ok  chadwick tools built")
        return
    _run(["autoreconf", "-i"], cwd=CHADWICK_SRC)
    _run(["./configure", f"--prefix={CHADWICK}"], cwd=CHADWICK_SRC)
    _run(["make", "-j4"], cwd=CHADWICK_SRC)
    _run(["make", "install"], cwd=CHADWICK_SRC)
    print("built chadwick tools")


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    _checkout(CFG["retrosheet"]["url"], CFG["retrosheet"]["sha"], RETROSHEET)
    _checkout(CFG["chadwick"]["url"], CFG["chadwick"]["sha"], CHADWICK_SRC)
    build_chadwick()


if __name__ == "__main__":
    main()
