#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="${APP_VERSION:-0.1.2}"
APP="${APP_PATH:-$ROOT_DIR/release/Kokoro MLX.app}"
DMG="${1:-$ROOT_DIR/release/Kokoro-MLX-$VERSION-arm64.dmg}"
PROFILE="${NOTARY_PROFILE:-}"
NOTARY_KEYCHAIN="${NOTARY_KEYCHAIN:-${HOME}/Library/Keychains/login.keychain-db}"
NOTARY_DIR="$ROOT_DIR/build/notary"
APP_ZIP="$NOTARY_DIR/Kokoro-MLX-$VERSION-arm64.zip"

if [[ -z "$PROFILE" ]]; then
  print -u2 "Set NOTARY_PROFILE to a notarytool Keychain profile."
  exit 1
fi

if [[ ! -f "$NOTARY_KEYCHAIN" ]]; then
  print -u2 "notarytool Keychain file does not exist: $NOTARY_KEYCHAIN"
  exit 1
fi

mkdir -p "$NOTARY_DIR"
rm -f "$APP_ZIP"

ditto -c -k --keepParent "$APP" "$APP_ZIP"
xcrun notarytool submit "$APP_ZIP" --keychain-profile "$PROFILE" --keychain "$NOTARY_KEYCHAIN" --wait
xcrun stapler staple "$APP"
xcrun stapler validate "$APP"

"$ROOT_DIR/packaging/create_dmg.sh" "$APP" "$DMG"
xcrun notarytool submit "$DMG" --keychain-profile "$PROFILE" --keychain "$NOTARY_KEYCHAIN" --wait
xcrun stapler staple "$DMG"
xcrun stapler validate "$DMG"
spctl --assess --type execute --verbose=2 "$APP"
spctl --assess --type open --context context:primary-signature --verbose=2 "$DMG"
printf 'Notarized %s and %s\n' "$APP" "$DMG"
