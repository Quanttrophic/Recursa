#!/usr/bin/env bash
# Build assets/recursa.icns from assets/recursa.png (macOS only: sips + iconutil).
set -euo pipefail
cd "$(dirname "$0")/.."
SET=assets/recursa.iconset
rm -rf "$SET" && mkdir -p "$SET"
for s in 16 32 128 256 512; do
  sips -z "$s" "$s" assets/recursa.png --out "$SET/icon_${s}x${s}.png" >/dev/null
  d=$((s * 2))
  sips -z "$d" "$d" assets/recursa.png --out "$SET/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$SET" -o assets/recursa.icns
rm -rf "$SET"
echo "assets/recursa.icns"
