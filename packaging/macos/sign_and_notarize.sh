#!/usr/bin/env bash
# Sign dist/Recursa.app with a Developer ID and notarize the disk image.
# Runs only when the Apple secrets are present (see BUILDING.md); otherwise the
# release ships unsigned and testers use right-click > Open the first time.
#   bash packaging/macos/sign_and_notarize.sh <Recursa.dmg>
set -euo pipefail
DMG=${1:?usage: sign_and_notarize.sh Recursa.dmg}
: "${APPLE_CERT_P12_BASE64:?}" "${APPLE_CERT_PASSWORD:?}" "${APPLE_SIGNING_IDENTITY:?}"
: "${APPLE_ID:?}" "${APPLE_TEAM_ID:?}" "${APPLE_APP_PASSWORD:?}"

KEYCHAIN=build.keychain
KC_PASS=$(openssl rand -hex 16)
echo "$APPLE_CERT_P12_BASE64" | base64 --decode > cert.p12
security create-keychain -p "$KC_PASS" "$KEYCHAIN"
security set-keychain-settings -lut 3600 "$KEYCHAIN"
security unlock-keychain -p "$KC_PASS" "$KEYCHAIN"
security import cert.p12 -k "$KEYCHAIN" -P "$APPLE_CERT_PASSWORD" -T /usr/bin/codesign
security set-key-partition-list -S apple-tool:,apple: -s -k "$KC_PASS" "$KEYCHAIN"
security list-keychains -d user -s "$KEYCHAIN" $(security list-keychains -d user | tr -d '"')
rm -f cert.p12

# Sign every nested binary first, then the app, with the hardened runtime.
find dist/Recursa.app/Contents -type f \( -name "*.so" -o -name "*.dylib" -o -perm -111 \) -print0 |
  xargs -0 -I{} codesign --force --timestamp --options runtime \
    --entitlements packaging/macos/entitlements.plist --sign "$APPLE_SIGNING_IDENTITY" "{}"
codesign --force --timestamp --options runtime --entitlements packaging/macos/entitlements.plist \
  --sign "$APPLE_SIGNING_IDENTITY" dist/Recursa.app
codesign --verify --deep --strict --verbose=2 dist/Recursa.app

bash packaging/macos/make_dmg.sh "$DMG"
codesign --force --timestamp --sign "$APPLE_SIGNING_IDENTITY" "$DMG"
xcrun notarytool submit "$DMG" --apple-id "$APPLE_ID" --team-id "$APPLE_TEAM_ID" \
  --password "$APPLE_APP_PASSWORD" --wait
xcrun stapler staple "$DMG"
echo "signed and notarized $DMG"
