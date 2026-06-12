#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$ROOT_DIR/build/macos"
DIST_DIR="$BUILD_DIR/pyinstaller-dist"
WORK_DIR="$BUILD_DIR/pyinstaller-work"
APP_DIR="$ROOT_DIR/release/Kokoro MLX.app"
CONTENTS="$APP_DIR/Contents"
VENV="${KOKORO_BUILD_VENV:-$ROOT_DIR/.build/macos-venv}"
MODEL_SOURCE="${KOKORO_MODEL_SOURCE:-}"
APP_BUILD_NUMBER="${APP_BUILD_NUMBER:-}"

if [[ ! -x "$VENV/bin/pyinstaller" ]]; then
  print -u2 "Missing build environment: $VENV"
  print -u2 "Run packaging/setup_build_env.sh first."
  exit 1
fi

rm -rf "$BUILD_DIR" "$APP_DIR"
mkdir -p "$BUILD_DIR" "$DIST_DIR" "$WORK_DIR" "$CONTENTS/MacOS" "$CONTENTS/Resources/Backend" "$ROOT_DIR/release"

"$ROOT_DIR/packaging/create_icon.sh" "$ROOT_DIR/logo.png" "$BUILD_DIR/AppIcon.icns"

if [[ -n "$MODEL_SOURCE" ]]; then
  "$VENV/bin/python" "$ROOT_DIR/packaging/prepare_model.py" "$BUILD_DIR/model" --source "$MODEL_SOURCE"
else
  "$VENV/bin/python" "$ROOT_DIR/packaging/prepare_model.py" "$BUILD_DIR/model"
fi

PYINSTALLER_CONFIG_DIR="$BUILD_DIR/pyinstaller-config" "$VENV/bin/pyinstaller" \
  --noconfirm \
  --clean \
  --distpath "$DIST_DIR" \
  --workpath "$WORK_DIR" \
  "$ROOT_DIR/packaging/kokoro_mlx_backend.spec"

CLANG_MODULE_CACHE_PATH="$BUILD_DIR/module-cache" \
SWIFT_MODULECACHE_PATH="$BUILD_DIR/module-cache" \
xcrun swiftc \
  -parse-as-library \
  -O \
  -target arm64-apple-macos15.0 \
  "$ROOT_DIR/macos/KokoroMLXApp.swift" \
  -o "$CONTENTS/MacOS/Kokoro MLX"

cp "$ROOT_DIR/macos/Info.plist" "$CONTENTS/Info.plist"
if [[ -n "$APP_BUILD_NUMBER" ]]; then
  /usr/libexec/PlistBuddy -c "Set :CFBundleVersion $APP_BUILD_NUMBER" "$CONTENTS/Info.plist" >/dev/null
fi
cp "$BUILD_DIR/AppIcon.icns" "$CONTENTS/Resources/AppIcon.icns"
cp -R "$DIST_DIR/kokoro-mlx-backend/." "$CONTENTS/Resources/Backend/"
cp -R "$BUILD_DIR/model" "$CONTENTS/Resources/model"
cp "$ROOT_DIR/LICENSE" "$CONTENTS/Resources/LICENSE"

chmod +x "$CONTENTS/MacOS/Kokoro MLX" "$CONTENTS/Resources/Backend/kokoro-mlx-backend"
printf 'Built %s\n' "$APP_DIR"
