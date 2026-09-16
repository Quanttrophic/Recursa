#!/usr/bin/env bash
# Local macOS build (Python 3.12 from python.org). Run from the repo root.
set -euo pipefail
PY=${PYTHON:-python3.12}
"$PY" -m venv .venv-build
./.venv-build/bin/pip install --upgrade pip
./.venv-build/bin/pip install -r requirements-build.txt
bash scripts/make_icns.sh
./.venv-build/bin/pyinstaller --noconfirm --clean recursa.spec
./dist/Recursa.app/Contents/MacOS/Recursa --selfcheck | tail -3
./dist/Recursa.app/Contents/MacOS/Recursa --smoke-test
mkdir -p release
bash packaging/macos/make_dmg.sh "release/Recursa-macos-$(uname -m).dmg"
