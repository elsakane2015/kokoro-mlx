#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP="${1:-$ROOT_DIR/release/Kokoro MLX.app}"
IDENTITY="${CODE_SIGN_IDENTITY:-Developer ID Application: Xuefeng Huang (HCDD4TQBT8)}"
ENTITLEMENTS="$ROOT_DIR/macos/entitlements.plist"

while IFS= read -r binary; do
  codesign --force --timestamp --options runtime --sign "$IDENTITY" "$binary"
done < <(find "$APP/Contents" -type f \( -name '*.so' -o -name '*.dylib' \) -print)

codesign --force --timestamp --options runtime --entitlements "$ENTITLEMENTS" --sign "$IDENTITY" \
  "$APP/Contents/Resources/Backend/kokoro-mlx-backend"
codesign --force --timestamp --options runtime --entitlements "$ENTITLEMENTS" --sign "$IDENTITY" \
  "$APP/Contents/MacOS/Kokoro MLX"
codesign --force --timestamp --options runtime --entitlements "$ENTITLEMENTS" --sign "$IDENTITY" "$APP"

codesign --verify --deep --strict --verbose=2 "$APP"
printf 'Signed %s\n' "$APP"
