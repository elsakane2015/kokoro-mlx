# macOS Packaging

These scripts build the complete offline Apple Silicon macOS application.
Build metadata is defined in `macos/AppConfig.xcconfig`.

## Prerequisites

- Apple Silicon Mac running macOS 15 or later
- Xcode command-line tools
- `uv`
- A valid Developer ID Application certificate
- A `notarytool` Keychain profile for formal distribution

Secrets and notarization credentials must remain in the macOS Keychain and
must never be stored in this repository.

## Build

```bash
packaging/setup_build_env.sh
KOKORO_MODEL_SOURCE=/path/to/Kokoro-82M-bf16/snapshot packaging/build_app.sh
packaging/review_app.sh
```

When `KOKORO_MODEL_SOURCE` is omitted, the build helper downloads the model
from Hugging Face. The prepared model keeps the weights, model metadata and
all 54 safetensors voices while removing duplicate `.pt` files and samples.

## One-shot Build

The main entrypoint supports two modes:

```bash
packaging/release.sh --local
packaging/release.sh --release
```

- `--local` builds an unsigned App and DMG for fast local testing.
- `--release` builds, signs, notarizes, and staples the distributable bundle.
- If no flag is provided, the script uses the signed release flow.

Both modes increment the build number automatically and write artifacts into a
new versioned `releases/vX.Y.Z-bNNN/` directory.

### Signed Release

```bash
NOTARY_PROFILE=PROFILE_NAME packaging/release.sh
```

This command performs the full release flow:

1. Verifies the configured Developer ID signing identity is present in the keychain.
2. Verifies the `notarytool` Keychain profile is usable.
3. Builds the App.
4. Signs the App and nested binaries.
5. Runs the local review checks.
6. Rebuilds, signs, notarizes, staples, and validates the DMG.

### Local Unsigned Build

```bash
packaging/release.sh --local
```

This skips the signing, review, and notarization steps. It is the preferred
path for ordinary local testing because it avoids the large Apple upload and
still produces a DMG that matches the app bundle built on disk.

## Sign and Create DMG

```bash
packaging/sign_app.sh
packaging/create_dmg.sh
```

The default signing identity is configured in the scripts and can be
overridden with `CODE_SIGN_IDENTITY`. The DMG includes the App, an Applications
shortcut, the user guide, project license and third-party notices.

## Notarize

Create a Keychain profile once:

```bash
xcrun notarytool store-credentials PROFILE_NAME --keychain ~/Library/Keychains/login.keychain-db
```

Then submit and staple the signed App and DMG:

```bash
NOTARY_PROFILE=PROFILE_NAME packaging/notarize.sh
```

The notarization script submits a ZIP containing the signed App, staples and
validates the App, rebuilds and signs the DMG, submits and staples the DMG,
then runs Gatekeeper assessment on both artifacts. Set `NOTARY_KEYCHAIN` if
your profile is stored outside the default login keychain.

## Review

Use `MACOS_APP_PACKAGING_TODO.md` as the release checklist. Do not mark a task
complete until its Review item has passed. A formal release is not complete
until the notarized DMG has also been tested on a clean Apple Silicon Mac that
does not have Python, Homebrew or developer tools installed.
