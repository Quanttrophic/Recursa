# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Recursa (NJ real-estate licensing exam trainer).

Build on each target platform (PyInstaller does not cross-compile). The
GitHub workflow in .github/workflows/build.yml does this for Windows and
both kinds of Mac, and publishes installers on a version tag.

    pip install -r requirements-build.txt
    pyinstaller --noconfirm --clean recursa.spec

Output:
    Windows / Linux : dist/Recursa/Recursa(.exe)   (a folder; zip it to send)
    macOS           : dist/Recursa.app

One-folder, not one-file, on purpose: a 49,000-line app starts noticeably
faster without unpacking itself on every launch, and Recursa's own restart
(after restoring a backup) re-executes itself, which one-file builds on
Windows handle badly because their temporary folder is deleted underneath.

What is deliberately NOT bundled: torch, transformers, sentence-transformers,
huggingface_hub and batchgen. They power optional local-model tiers, add
several gigabytes, and Recursa already degrades cleanly without them (and can
use the private GPU gateway instead).
"""
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

APP_NAME = "Recursa"
APP_MODULE = "recursa_app"
APP_VERSION = "9.9.1"
BUNDLE_ID = "com.bearproperties.recursa"
HERE = os.path.abspath(SPECPATH)
SRC = os.path.join(HERE, "src")
APP_VERSION = os.environ.get("RECURSA_VERSION", APP_VERSION).lstrip("v")

icon_win = os.path.join(HERE, "assets", "recursa.ico")
icon_mac = os.path.join(HERE, "assets", "recursa.icns")

datas = []
datas += collect_data_files("customtkinter")          # themes and fonts CustomTkinter loads at runtime
datas += collect_data_files("fsrs")

hiddenimports = [APP_MODULE]
hiddenimports += collect_submodules("keyring.backends")   # the OS keychain backend is chosen at runtime
hiddenimports += collect_submodules("fsrs")
hiddenimports += ["darkdetect", "packaging", "psutil", "httpx", "pydantic", "rank_bm25", "rapidfuzz", "pypdf"]
if sys.platform == "win32":
    hiddenimports += ["win32ctypes.core", "winsound"]

excludes = [
    "torch", "torchvision", "torchaudio", "transformers", "sentence_transformers",
    "huggingface_hub", "batchgen", "tensorflow", "jax", "scipy", "pandas",
    "matplotlib", "IPython", "notebook", "pytest",
    "numpy", "yaml",                 # pulled in transitively by hooks, never imported by Recursa
]

a = Analysis(
    ["recursa_launcher.py"],
    pathex=[HERE, SRC],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
    # Keep the app module as a readable .py file inside the bundle: the
    # self-check's probes read the module's own source.
    module_collection_mode={APP_MODULE: "py"},
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                       # UPX-packed executables trip antivirus heuristics
    console=False,                   # no terminal window behind the app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,                # build natively; set "universal2" only with a universal Python
    codesign_identity=None,          # signing happens after the build (see .github/workflows/build.yml)
    entitlements_file=None,
    icon=(icon_win if sys.platform == "win32" and os.path.exists(icon_win)
          else icon_mac if sys.platform == "darwin" and os.path.exists(icon_mac) else None),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        icon=icon_mac if os.path.exists(icon_mac) else None,
        bundle_identifier=BUNDLE_ID,
        version=APP_VERSION,
        info_plist={
            "CFBundleName": APP_NAME,
            "CFBundleDisplayName": APP_NAME,
            "CFBundleShortVersionString": APP_VERSION,
            "CFBundleVersion": APP_VERSION,
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
            "NSRequiresAquaSystemAppearance": False,
        },
    )
