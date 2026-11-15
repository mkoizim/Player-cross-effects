"""Check that regenerated reports match the committed ones.

Run after `make describe models`. Tables and every other text output must be
byte-identical to the committed version. Figures (PNG) must be pixel-identical:
PNG compression can differ between machines while the image does not, so their
bytes are not compared. Any new, missing or changed file fails the check.
"""

import io
import subprocess
import sys

import numpy as np
from PIL import Image


def _git(*args: str) -> bytes:
    return subprocess.run(["git", *args], check=True, capture_output=True).stdout


def _pixels(data: bytes) -> np.ndarray:
    return np.asarray(Image.open(io.BytesIO(data)).convert("RGBA"))


def main() -> int:
    status = _git("status", "--porcelain", "--untracked-files=all", "--", "reports/")
    problems = []
    same_pixels = 0
    for line in status.decode().splitlines():
        code, path = line[:2], line[3:]
        if code.strip() != "M":
            problems.append(f"{path}: {'new, not committed' if code == '??' else 'missing or renamed'}")
            continue
        if not path.endswith(".png"):
            problems.append(f"{path}: content differs")
            continue
        old, new = _pixels(_git("show", f"HEAD:{path}")), _pixels(open(path, "rb").read())
        if old.shape != new.shape:
            problems.append(f"{path}: size {old.shape[1]}x{old.shape[0]} -> {new.shape[1]}x{new.shape[0]}")
        elif not np.array_equal(old, new):
            n = int(np.any(old != new, axis=-1).sum())
            problems.append(f"{path}: {n:,} of {old.shape[0] * old.shape[1]:,} pixels differ")
        else:
            same_pixels += 1

    print(f"reports/: {same_pixels} figure(s) re-encoded with identical pixels; "
          f"{len(problems)} problem(s).")
    for p in problems:
        print("FAIL", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
