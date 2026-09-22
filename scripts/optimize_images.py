#!/usr/bin/env python3
"""Resize and compress an image for the web.

Usage:
    python3 scripts/optimize_images.py SOURCE DEST [--width 1600]

DEST's extension picks the format (.webp or .jpg). Transparent images are
flattened onto white, so paper figures stay readable on any background.
Keep full-size originals in private/ (gitignored); commit only the output.
Requires Pillow (pip install pillow).
"""
import argparse
from pathlib import Path

from PIL import Image

Image.MAX_IMAGE_PIXELS = None  # some paper figures are exported at print resolution


def optimize(src: Path, dest: Path, width: int = 1600) -> tuple[int, int]:
    im = Image.open(src)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        white = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(white, im)
    im = im.convert("RGB")
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.suffix.lower() == ".webp":
        im.save(dest, "WEBP", quality=82, method=6)
    else:
        im.save(dest, "JPEG", quality=84, optimize=True, progressive=True)
    return im.size


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", type=Path)
    ap.add_argument("dest", type=Path)
    ap.add_argument("--width", type=int, default=1600)
    a = ap.parse_args()
    w, h = optimize(a.source, a.dest, a.width)
    print(f"{a.dest}  {w}x{h}  {a.dest.stat().st_size // 1024} KB")
