#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT_DIR/release/Kokoro MLX.app"
XC_CONFIG="$ROOT_DIR/macos/AppConfig.xcconfig"

read_xcconfig_value() {
  local key="$1"
  awk -F' = ' -v wanted="$key" '$1 == wanted { print $2; exit }' "$XC_CONFIG"
}

APP_VERSION="${APP_VERSION:-$(read_xcconfig_value APP_VERSION)}"
CODE_SIGN_IDENTITY="${CODE_SIGN_IDENTITY:-$(read_xcconfig_value CODE_SIGN_IDENTITY)}"
NOTARY_PROFILE="${NOTARY_PROFILE:-}"
NOTARY_KEYCHAIN="${NOTARY_KEYCHAIN:-${HOME}/Library/Keychains/login.keychain-db}"

usage() {
  cat <<'EOF'
Usage:
  packaging/release.sh                Build, sign, notarize, and staple the macOS app

Environment:
  APP_VERSION=0.1.2
  CODE_SIGN_IDENTITY="Developer ID Application: ..."
  NOTARY_PROFILE=AC_PASSWORD
  NOTARY_KEYCHAIN=/path/to/login.keychain-db
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ -z "${APP_VERSION}" ]]; then
  echo "ERROR: APP_VERSION is empty."
  exit 1
fi

if [[ -z "${CODE_SIGN_IDENTITY}" ]]; then
  echo "ERROR: CODE_SIGN_IDENTITY is empty."
  exit 1
fi

if [[ "${CODE_SIGN_IDENTITY}" != "Developer ID Application:"* ]]; then
  echo "ERROR: macOS release builds require a Developer ID Application identity."
  echo "  ${CODE_SIGN_IDENTITY}"
  exit 1
fi

TEAM_ID="$(printf '%s\n' "${CODE_SIGN_IDENTITY}" | sed -n 's/.*(\([A-Z0-9][A-Z0-9]*\))$/\1/p')"
if [[ -z "${TEAM_ID}" ]]; then
  echo "ERROR: could not read Team ID from signing identity:"
  echo "  ${CODE_SIGN_IDENTITY}"
  exit 1
fi

if ! security find-identity -v -p codesigning | grep -F "\"${CODE_SIGN_IDENTITY}\"" >/dev/null; then
  echo "ERROR: signing identity is not available in the keychain:"
  echo "  ${CODE_SIGN_IDENTITY}"
  exit 1
fi

if [[ -z "${NOTARY_PROFILE}" ]]; then
  echo "ERROR: NOTARY_PROFILE is required."
  echo "Set it to a notarytool Keychain profile, for example AC_PASSWORD."
  exit 1
fi

if [[ ! -f "${NOTARY_KEYCHAIN}" ]]; then
  echo "ERROR: notarytool Keychain file does not exist:"
  echo "  ${NOTARY_KEYCHAIN}"
  exit 1
fi

NOTARY_PROFILE_READY=false
for attempt in 1 2 3; do
  if xcrun notarytool history \
    --keychain-profile "${NOTARY_PROFILE}" \
    --keychain "${NOTARY_KEYCHAIN}" \
    --output-format json >/dev/null; then
    NOTARY_PROFILE_READY=true
    break
  fi
  if [[ "${attempt}" -lt 3 ]]; then
    echo "Notary profile validation failed (attempt ${attempt}/3); retrying..."
    sleep 2
  fi
done
if [[ "${NOTARY_PROFILE_READY}" != true ]]; then
  echo "ERROR: notarytool Keychain profile is unavailable or invalid:"
  echo "  ${NOTARY_PROFILE}"
  echo "Keychain: ${NOTARY_KEYCHAIN}"
  echo "Store or refresh it with:"
  echo "  xcrun notarytool store-credentials ${NOTARY_PROFILE} --team-id ${TEAM_ID} --keychain ${NOTARY_KEYCHAIN}"
  exit 1
fi

export APP_VERSION CODE_SIGN_IDENTITY NOTARY_PROFILE NOTARY_KEYCHAIN

echo "Signing identity: ${CODE_SIGN_IDENTITY}"
echo "Notary profile: ${NOTARY_PROFILE} (${NOTARY_KEYCHAIN})"

"${ROOT_DIR}/packaging/build_app.sh"
"${ROOT_DIR}/packaging/sign_app.sh" "$APP"
"${ROOT_DIR}/packaging/review_app.sh" "$APP"
APP_PATH="$APP" "${ROOT_DIR}/packaging/notarize.sh"
