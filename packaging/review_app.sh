#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP="${1:-$ROOT_DIR/release/Kokoro MLX.app}"
CONTENTS="$APP/Contents"
APP_BUILD_NUMBER="${APP_BUILD_NUMBER:-}"

test -x "$CONTENTS/MacOS/Kokoro MLX"
test -x "$CONTENTS/Resources/Backend/kokoro-mlx-backend"
test -f "$CONTENTS/Resources/model/config.json"
test -f "$CONTENTS/Resources/model/kokoro-v1_0.safetensors"
test "$(find "$CONTENTS/Resources/model/voices" -name '*.safetensors' | wc -l | tr -d ' ')" = "54"
test "$(find "$CONTENTS/Resources/model" -name '*.pt' | wc -l | tr -d ' ')" = "0"
test ! -d "$CONTENTS/Resources/Backend/_internal/torch"
test ! -d "$CONTENTS/Resources/Backend/_internal/pytest"
test ! -d "$CONTENTS/Resources/Backend/_internal/ruff"

plutil -lint "$CONTENTS/Info.plist"
test "$(plutil -extract CFBundleIdentifier raw "$CONTENTS/Info.plist")" = "com.litotime.kokoromlx"
if [[ -n "$APP_BUILD_NUMBER" ]]; then
  test "$(plutil -extract CFBundleVersion raw "$CONTENTS/Info.plist")" = "$APP_BUILD_NUMBER"
fi
file "$CONTENTS/MacOS/Kokoro MLX" | grep -q arm64
file "$CONTENTS/Resources/Backend/kokoro-mlx-backend" | grep -q arm64

printf 'App size: '
du -sh "$APP"
printf 'App review passed: %s\n' "$APP"
