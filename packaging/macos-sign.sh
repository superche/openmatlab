#!/bin/bash
set -euo pipefail
case "${1:?import or notarize}" in
  import)
    : "${APPLE_CERTIFICATE_BASE64:?}" "${APPLE_CERTIFICATE_PASSWORD:?}" "${APPLE_SIGNING_IDENTITY:?}"
    keychain="$RUNNER_TEMP/openmatlab-signing.keychain-db"
    password=$(openssl rand -hex 32)
    echo "::add-mask::$password"
    printf '%s' "$APPLE_CERTIFICATE_BASE64" | base64 --decode > "$RUNNER_TEMP/certificate.p12"
    security create-keychain -p "$password" "$keychain"
    security set-keychain-settings -lut 21600 "$keychain"
    security unlock-keychain -p "$password" "$keychain"
    security import "$RUNNER_TEMP/certificate.p12" -P "$APPLE_CERTIFICATE_PASSWORD" -A -t cert -f pkcs12 -k "$keychain"
    security set-key-partition-list -S apple-tool:,apple:,codesign: -k "$password" "$keychain"
    security list-keychains -d user -s "$keychain" login.keychain-db
    rm "$RUNNER_TEMP/certificate.p12"
    ;;
  notarize)
    : "${APPLE_ID:?}" "${APPLE_TEAM_ID:?}" "${APPLE_APP_PASSWORD:?}" "${APPLE_SIGNING_IDENTITY:?}"
    app=dist/OpenMATLAB.app
    codesign --verify --deep --strict --verbose=2 "$app"
    ditto -c -k --keepParent "$app" "$RUNNER_TEMP/notarize.zip"
    xcrun notarytool submit "$RUNNER_TEMP/notarize.zip" --apple-id "$APPLE_ID" --team-id "$APPLE_TEAM_ID" --password "$APPLE_APP_PASSWORD" --wait --timeout 30m
    xcrun stapler staple "$app"
    xcrun stapler validate "$app"
    spctl --assess --type execute --verbose=2 "$app"
    ;;
  *) exit 2 ;;
esac
