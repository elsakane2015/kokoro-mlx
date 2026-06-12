#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP="${1:-$ROOT_DIR/release/Kokoro MLX.app}"
VERSION="${APP_VERSION:-0.1.2}"
DMG="${2:-$ROOT_DIR/release/Kokoro-MLX-$VERSION-arm64.dmg}"
STAGING="$ROOT_DIR/build/dmg"
IDENTITY="${CODE_SIGN_IDENTITY:-Developer ID Application: Xuefeng Huang (HCDD4TQBT8)}"
VENV="${KOKORO_BUILD_VENV:-$ROOT_DIR/.build/macos-venv}"
THIRD_PARTY_DIR="$STAGING/Third-Party Licenses"
SIGN_DMG="${SIGN_DMG:-1}"

rm -rf "$STAGING" "$DMG"
mkdir -p "$STAGING" "$THIRD_PARTY_DIR"
cp -R "$APP" "$STAGING/"
ln -s /Applications "$STAGING/Applications"
cp "$ROOT_DIR/MACOS_APP_USER_GUIDE.md" "$STAGING/使用说明.md"
cp "$ROOT_DIR/THIRD_PARTY_NOTICES.md" "$STAGING/THIRD_PARTY_NOTICES.md"
cp "$ROOT_DIR/LICENSE" "$STAGING/LICENSE"

if [[ ! -x "$VENV/bin/python" ]]; then
  print -u2 "Missing build environment for third-party licenses: $VENV"
  exit 1
fi

SITE_PACKAGES="$("$VENV/bin/python" -c 'import site; print(site.getsitepackages()[0])')"
while IFS= read -r license; do
  relative="${license#$SITE_PACKAGES/}"
  destination="$THIRD_PARTY_DIR/$relative"
  mkdir -p "$(dirname "$destination")"
  cp "$license" "$destination"
done < <(find "$SITE_PACKAGES" -type f \( \
  -iname 'LICENSE*' -o -iname 'LICENCE*' -o -iname 'COPYING*' -o -iname 'NOTICE*' \
\) -print)

cp "$APP/Contents/Resources/model/README.md" "$THIRD_PARTY_DIR/Kokoro-Model-README.md"

hdiutil create -volname "Kokoro MLX" -srcfolder "$STAGING" -ov -format UDZO "$DMG"
if [[ "$SIGN_DMG" != "0" ]]; then
  codesign --force --timestamp --sign "$IDENTITY" "$DMG"
  codesign --verify --verbose=2 "$DMG"
fi
shasum -a 256 "$DMG" > "$ROOT_DIR/release/SHA256SUMS"
printf 'Created %s\n' "$DMG"
