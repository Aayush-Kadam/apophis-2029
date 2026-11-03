# Start APOPHIS 2029 on Windows

**Scope:** These directions apply to a complete locally generated static application bundle. The public source-only ZIP does not contain the static application's `index.html`, compiled assets or JPL-derived snapshots. Follow the root README to acquire your own data and build the bundle first; do not try to launch the source ZIP as if it were the separate private app ZIP.

The ZIP has one application folder: **APOPHIS_2029**. Its entry point is **APOPHIS_2029/index.html**. Keep assets, snapshots, launchers and notices beside index.html.

## Extract first

1. Right-click the ZIP in File Explorer and choose **Extract All**.
2. Extract into a new folder; do not launch from inside the ZIP viewer.
3. Open **APOPHIS_2029**. Confirm index.html, assets, snapshots, START_APOPHIS.cmd and launch_apophis.py are present together.

Python 3.9 or newer is required only for the local server. The static application requires no pip or npm installation. The scientific source pipeline separately uses its pinned Python 3.12 environment. Install Python from https://www.python.org/downloads/windows/ if necessary; this launcher does not install software.

## Optional launcher: recommended

Double-click **START_APOPHIS.cmd**. It finds the Windows py launcher or python, verifies the frozen snapshot, and serves the folder containing itself. It does not depend on the terminal's current directory. It opens http://127.0.0.1:8765/ in the default browser.

Keep the terminal window open while using the app. Press **Ctrl+C** there to stop. The server listens only on 127.0.0.1 and makes no JPL requests.

If port 8765 is occupied, invoke the launcher with --port 8766. In PowerShell, replacing the example path with your actual extraction location:

```powershell
& "C:\Your extracted folder\APOPHIS_2029\START_APOPHIS.cmd" --port 8766
```

The Python-only launcher is also independent of the current directory:

```powershell
py -3 "C:\Your extracted folder\APOPHIS_2029\launch_apophis.py" --no-browser --port 8766
```

## Manual alternative

Open a PowerShell terminal in the **APOPHIS_2029 folder that contains index.html**, then run:

```powershell
py -3 -m http.server 8765 --bind 127.0.0.1 --directory .
```

Open http://127.0.0.1:8765/. If py is unavailable but python --version reports Python 3, replace py -3 with python.

From any other directory, explicitly supply the full application path:

```powershell
py -3 -m http.server 8765 --bind 127.0.0.1 --directory "C:\Your extracted folder\APOPHIS_2029"
```

Do not serve the outer extraction folder: that produces a directory listing. Do not double-click index.html; local-file browser restrictions can prevent data loading. Use the printed HTTP URL instead.

## Check that the right app opened

The page title is **APOPHIS 2029 — The Near-Miss Engine**. The header shows safe-flyby status and frozen solution **220**. Click **Closest approach**: Earth-center distance should read about **38,011.3 km**, relative speed **7.423 km/s**. Open **Evidence** to inspect the snapshot record.

All runtime assets and frozen data are local. No Internet connection is needed after Python and a browser are installed. Reload requires the local server to remain running.

## Troubleshooting

- Directory listing or wrong page: use the folder containing index.html, or use START_APOPHIS.cmd.
- Address already in use: choose another port. The launcher does not silently reuse an unrelated server.
- Snapshot missing/hash mismatch: extract the complete matching ZIP into a new folder. Do not mix versions.
- 3D unavailable: the same numerical readouts and a 2D projection remain available; do not change browser security settings.
- Python not found: install a normal Python 3; scientific dependencies are unnecessary for static serving.

Original owned code: Copyright 2026 Aayush Kadam, Apache-2.0. NASA/JPL data and external components retain separate terms and attribution in NOTICE and THIRD_PARTY_NOTICES.md. A local launcher is not authorization for public publication.
