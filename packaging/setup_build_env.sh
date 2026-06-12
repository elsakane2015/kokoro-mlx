#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${KOKORO_BUILD_VENV:-$ROOT_DIR/.build/macos-venv}"
UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/kokoro-uv-cache}"

rm -rf "$VENV"
uv venv --python 3.12 "$VENV"
UV_CACHE_DIR="$UV_CACHE_DIR" uv pip install --python "$VENV/bin/python" \
  -e "${ROOT_DIR}[web,multilingual]" \
  pyinstaller \
  httpx

UV_CACHE_DIR="$UV_CACHE_DIR" uv pip install --python "$VENV/bin/python" \
  "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl"

uv pip uninstall --python "$VENV/bin/python" torch torchgen networkx sympy mpmath spacy-curated-transformers

"$VENV/bin/python" -c "import pyopenjtalk; pyopenjtalk._lazy_init()"

printf 'Prepared isolated build environment: %s\n' "$VENV"
