#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE="${1:-$ROOT_DIR/logo.png}"
OUTPUT="${2:-$ROOT_DIR/build/macos/AppIcon.icns}"
ICONSET="${OUTPUT:r}.iconset"
VENV="${KOKORO_BUILD_VENV:-$ROOT_DIR/.build/macos-venv}"

rm -rf "$ICONSET"
mkdir -p "$ICONSET" "${OUTPUT:h}"

for size in 16 32 128 256 512; do
  sips -z "$size" "$size" "$SOURCE" --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
  retina=$((size * 2))
  sips -z "$retina" "$retina" "$SOURCE" --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
done

"$VENV/bin/python" "$ROOT_DIR/packaging/create_icns.py" "$ICONSET" "$OUTPUT"
rm -rf "$ICONSET"
printf 'Created %s\n' "$OUTPUT"
