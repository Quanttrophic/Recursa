# Building and releasing Recursa

## Layout

| Path | What it is |
|---|---|
| `src/recursa_app.py` | The application |
| `recursa_launcher.py` | Entry point, with `--selfcheck`, `--smoke-test` and `--report=PATH` |
| `recursa.spec` | PyInstaller build (one folder; `.app` on macOS) |
| `requirements-build.txt` | Pinned packages (Python 3.12) |
| `assets/recursa.png`, `assets/recursa.ico` | App icon (`.icns` is generated on macOS by `scripts/make_icns.sh`) |
| `packaging/windows/recursa.iss` | Inno Setup installer: per-user, Start menu, optional desktop shortcut, uninstaller |
| `packaging/windows/sign.ps1` | Authenticode signing, used when a certificate secret exists |
| `packaging/macos/make_dmg.sh` | Drag-to-Applications disk image |
| `packaging/macos/sign_and_notarize.sh`, `entitlements.plist` | Developer ID signing and notarization, used when Apple secrets exist |
| `.github/workflows/build.yml` | Builds, checks and releases |
| `scripts/build_local_windows.ps1`, `scripts/build_local_macos.sh` | Local builds |

## How the workflow runs

| Trigger | Result |
|---|---|
| Push to `main`, a pull request, or **Run workflow** by hand | Builds on Windows x64, macOS Apple silicon (`macos-15`) and macOS Intel (`macos-15-intel`). Every build runs the frozen app's 105-class self-check and a window smoke test. Builds are kept as artifacts for 14 days. |
| Pushing a tag like `v9.5.0` | Also builds the Windows installer and portable zip and a `.dmg` per Mac chip, signs them if secrets are set, writes `SHA256SUMS.txt`, and publishes a GitHub Release. |

To make a release:

```bash
git tag v9.5.0
git push origin v9.5.0
```

**Intel Macs:** `macos-15-intel` is GitHub's last Intel image, available until August 2027. After that, drop the Intel leg or build Intel copies on your own Mac.

## Optional signing secrets
Add these under repository **Settings → Secrets and variables → Actions**. Without them, releases are unsigned and testers follow the first-open steps in the README.

**Windows:**
- `WINDOWS_CERT_PFX_BASE64`: your code-signing `.pfx` file, base64-encoded (`base64 -i cert.pfx`)
- `WINDOWS_CERT_PASSWORD`

**macOS** (needs Apple Developer Program membership):
- `APPLE_CERT_P12_BASE64`: a "Developer ID Application" certificate exported as `.p12`, base64-encoded
- `APPLE_CERT_PASSWORD`
- `APPLE_SIGNING_IDENTITY`: e.g. `Developer ID Application: Your Name (TEAMID)`
- `APPLE_ID`, `APPLE_TEAM_ID`
- `APPLE_APP_PASSWORD`: an app-specific password from appleid.apple.com

The signing scripts have not been run against real certificates. Expect to adjust them on the first signed release.

## Local builds
- **Windows:** `powershell -ExecutionPolicy Bypass -File scripts\build_local_windows.ps1`. For the installer, install Inno Setup 6, then run `iscc packaging\windows\recursa.iss`.
- **macOS:** `bash scripts/build_local_macos.sh`

## What was verified before this repository was handed over
- **Linux build from this exact layout** (Python 3.12.3, PyInstaller 6.22.3):
  - the frozen app passes all 105 self-check classes, including probes that read the app's own source;
  - the smoke test opens Today, Map, Practice, Insights and Settings;
  - a normal launch creates the learner database.
- **Workflow:** lints clean with actionlint. The only flag was the `macos-15-intel` label, which is newer than that actionlint release.
- **Not yet run:** the Windows and macOS jobs, the Inno Setup compile and the signing steps. The first workflow run is their test.

## Deliberately not bundled
torch, transformers, sentence-transformers, huggingface_hub and batchgen. They serve optional local-model tiers, add gigabytes, and Recursa runs fully without them.
