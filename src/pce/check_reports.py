"""Check that regenerated reports match the committed ones.

Run after `make describe models`. Every table, and every figure's record of what it plots
(`reports/figures/*.json`, written by `pce.describe.save`), must be byte-identical to the
committed version. Figure PNGs are not compared: the same plot rasterizes to different pixels
on different machines (fonts, anti-aliasing), so a PNG only has to exist, open as an image
and have a record. Any new or missing report fails.
"""

import subprocess
import sys
from pathlib import Path

from PIL import Image


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def main() -> int:
    problems = []
    redrawn = 0
    for line in _git("status", "--porcelain", "--untracked-files=all", "--", "reports/").splitlines():
        code, path = line[:2], line[3:]
        if code.strip() != "M":
            problems.append(f"{path}: {'new, not committed' if code == '??' else 'missing or renamed'}")
        elif path.endswith(".png"):
            redrawn += 1
        else:
            problems.append(f"{path}: content differs")
            if path.endswith(".json"):
                diff = _git("diff", "--no-color", "-U0", "--", path).splitlines()[4:24]
                problems.extend(f"    {d}" for d in diff)

    figures = Path("reports/figures")
    for png in sorted(figures.glob("*.png")):
        if not png.with_suffix(".json").exists():
            problems.append(f"{png}: no record of what it plots (.json)")
        try:
            Image.open(png).verify()
        except Exception as e:  # noqa: BLE001 - any decode failure is a failed report
            problems.append(f"{png}: not a readable image ({e})")
    for rec in sorted(figures.glob("*.json")):
        if not rec.with_suffix(".png").exists():
            problems.append(f"{rec}: record without a figure")

    print(f"reports/: {redrawn} figure(s) redrawn with different pixels (not compared); "
          f"{sum(not p.startswith('    ') for p in problems)} problem(s).")
    for p in problems:
        print(p if p.startswith("    ") else f"FAIL {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
