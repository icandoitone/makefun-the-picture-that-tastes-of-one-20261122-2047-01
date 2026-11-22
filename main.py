#!/usr/bin/env python3
"""One Strawberry, Dripping.

Writes the entry image to the output directory.

The image (entry.png, 1024x1024) is already built and stored in this
repository next to this program. This program simply copies those
bytes to the output directory, so the result is byte-identical to
entry.png on every run.

Pure Python standard library only — no third-party imports, no
network, no timestamps, no randomness. The repository is read-only
at grading time, so nothing is written back into it.

Output: $MAKEFUN_OUTPUT_DIR/entry.png (default /output/entry.png).
The output is verified byte-for-byte against the source image before
the program exits, so a truncated or partial write can never pass
silently.

Run:  python3 -P -s main.py
"""

import os
from pathlib import Path


def main() -> None:
    src = Path(__file__).resolve().parent / "entry.png"
    data = src.read_bytes()
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "entry.png"
    out.write_bytes(data)
    # Guard: the written file must be exactly the source image.
    if out.stat().st_size != len(data) or out.read_bytes() != data:
        raise SystemExit("output does not match entry.png")
    print(f"wrote {out} ({len(data)} bytes)")


if __name__ == "__main__":
    main()
