"""Create a modern PNG-backed ICNS file from an iconset directory."""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

ICNS_IMAGES = {
    "icp4": "icon_16x16.png",
    "icp5": "icon_32x32.png",
    "icp6": "icon_32x32@2x.png",
    "ic07": "icon_128x128.png",
    "ic08": "icon_256x256.png",
    "ic09": "icon_512x512.png",
    "ic10": "icon_512x512@2x.png",
}


def build_icns(iconset: Path, output: Path) -> None:
    chunks = []
    for icon_type, filename in ICNS_IMAGES.items():
        payload = (iconset / filename).read_bytes()
        chunks.append(icon_type.encode("ascii") + struct.pack(">I", len(payload) + 8) + payload)
    body = b"".join(chunks)
    output.write_bytes(b"icns" + struct.pack(">I", len(body) + 8) + body)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("iconset", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build_icns(args.iconset, args.output)


if __name__ == "__main__":
    main()
