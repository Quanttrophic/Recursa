#!/usr/bin/env bash
# Package dist/Recursa.app into a drag-to-Applications disk image.
#   bash packaging/macos/make_dmg.sh <output.dmg>
set -euo pipefail
OUT=${1:?usage: make_dmg.sh output.dmg}
STAGE=$(mktemp -d)
cp -R dist/Recursa.app "$STAGE/"
ln -s /Applications "$STAGE/Applications"
hdiutil create -volname "Recursa" -srcfolder "$STAGE" -ov -format UDZO "$OUT"
rm -rf "$STAGE"
echo "$OUT"
