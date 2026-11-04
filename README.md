# APOPHIS 2029 — Dual-Mode Observatory

**v0.2.0 publication candidate — original analytic education, with an explicitly local scientific-data workflow.**

This is the prepared v0.2.0 release candidate; publication requires owner approval. The earlier public `v0.1.0-source` release remains a separate preserved release. Original owned code is Apache-2.0, Copyright 2026 Aayush Kadam; see [LICENSE](LICENSE), [NOTICE](NOTICE) and [third-party notices](THIRD_PARTY_NOTICES.md).

## Two unmistakable modes

| Mode | Included content | Scientific status |
|---|---|---|
| Educational Explorer | Original analytic trajectory, procedural globe, 2D/3D renderer and explanations | **EDUCATIONAL DEMONSTRATION — NOT VERIFIED APOPHIS EPHEMERIDES** |
| Verified Reconstruction · local files | User selects a supported manifest and payload; no observational data ships here | Historical byte match is distinguished from compatible, unauthenticated local data |

Educational mode runs immediately after the static app is built/served, without any dataset or external service. Its original polynomial uses x=12t, y=24000+0.0001t², z=6000 km; velocities are exact derivatives, and t is relative example time in seconds. These illustrative values are not JPL observations, an orbit determination, or an impact prediction. The default 2D view allocates no WebGL context. 3D supports orbit/zoom, four camera modes, quality selection and context-loss fallback. Both modes have playback, pause, rewind, closest-approach navigation, keyboard timeline control and clear mode labels.

## Windows setup and launch

Prerequisites: Python 3.12 for science/tests, Node 24, pnpm 11.25.0. A Python 3.9+ interpreter suffices for the static server. Open PowerShell in the extracted `apophis-2029` source directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
cd web
pnpm install --frozen-lockfile
pnpm run build
cd ..
.\.venv\Scripts\python.exe launchers/b2/launch_observatory.py --directory web/dist --no-browser --port 8870
```

Open <http://127.0.0.1:8870/>. Keep the server terminal open and stop it with Ctrl+C. Dependency setup requires network access or matching cached packages. Do not open index.html directly with file://. The helper binds only loopback; it does not retrieve data, install software or host a public website.

The separately supplied static candidate ZIP contains `APOPHIS_OBSERVATORY/index.html`, `assets/`, notices and a launcher. Extract it fully, then double-click `APOPHIS_OBSERVATORY/START_OBSERVATORY.cmd`, or run `py -3 "C:\Your extracted folder\APOPHIS_OBSERVATORY\launch_observatory.py" --no-browser`. It serves its own directory independently of the terminal location. If port 8870 is occupied, pass `--port 8871`. The original `launchers/windows` scripts/tests remain unchanged for the separate historical data-bearing application; use `launchers/b2` for this candidate.

## Local scientific-data import

Click **Verified Reconstruction · load local files**. Select exactly `manifest.json` and `encounter.json`, acknowledge the local-read consent checkbox, then choose **Validate and open**. Files are read in browser memory only. They are not uploaded, persisted or used in analytics; the app has no JPL API calls. Clear local data removes app references, and reload returns to educational mode. Operating-system/driver memory release is not an immediate zero-RAM guarantee.

Supported export format: manifest and payload schema 1.0; orbit 220; Earth-centered ICRF / FRAME, geometric NONE; TDB; km, km/s and seconds; coarse 865 × 300-second rows and fine 1441 × 10-second rows, with the original 2029-Apr-12 TDB reference epoch. Validation checks filenames, size caps (16 KiB manifest / 4 MiB payload), UTF-8, JSON complexity/unsafe keys, numeric finiteness, ordering/cadence/windows, coordinate/time contracts, result consistency, source signatures/versions and provenance. Missing or incompatible provenance is rejected as unverified, not silently promoted to a verified record. See [input format and privacy](docs/B2_INPUT_AND_PRIVACY.md).

A compatible payload that differs from the release's reviewed historical digest is **UNVERIFIED LOCAL DATA**. User-supplied provenance and a matching user manifest cannot authenticate origin. An exact historical payload byte match is labeled separately against the fixed maintainer-review digest; it is not a JPL digital signature or a new independent orbital validation. No imported file is automatically official, and import never grants redistribution rights.

Users may independently prepare their own appropriate export using `tools/source_release.py`, with their own legitimate runtime contact and in accordance with the current [JPL API policy](https://ssd-api.jpl.nasa.gov/). The acquisition workflow requires external access and makes five necessary sequential requests; it is separate from the browser, which calls no JPL API. Do not run acquisition concurrently, redundantly, or as part of a browser test. API availability and future access to orbit 220 are not guaranteed. This B2 milestone makes **no new JPL data requests**.

## Tests and scientific preservation

Public Python test collection:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The source package contains all original test assertions. Without historical private inputs, 59 data-independent Python tests pass and 53 authentic-data checks explicitly skip. This is not equivalent to the separately preserved 112/112 private scientific suite. Historical inputs and results are deliberately absent; see [TESTING.md](TESTING.md).

Public dual-mode/invalid-input tests:

```powershell
cd web
node --experimental-strip-types tests/dual-mode.test.ts
cd ..
```

These execute the independent analytic example and malformed-input cases. The authentic-fixture campaign explicitly skips unless `APOPHIS_PRIVATE_FIXTURE_DIR` points to separately held `manifest.json` and `encounter.json`. No test downloads observations. The existing `pnpm run test:science` is an authentic-data-dependent 240-epoch comparison and needs that payload separately placed in `web/public/snapshots` in an isolated **private** validation tree. Never put private files there before making a public build/package.

The original Python calculations and client interpolation formulas are preserved. The private 112-test suite, 240 Python/client comparisons and two network-blocked reproductions are recorded separately. They validate the nominal orbit-220 reconstruction, not a new orbit solution or impact-risk assessment. Horizons and CAD share a model lineage. The educational mode is tested independently and carries no fabricated source/CAD uncertainty claims.

See [browser and memory reproduction](docs/B2_BROWSER_AND_MEMORY.md) for the independent local Playwright campaign and exact evidence scope. Do not call simulated/unit checks browser acceptance. The existing approximately 400 MiB absolute browser working-set target remains unmet; incremental metrics are additional reporting, not an approved replacement threshold. No portable FPS, universal device or zero-memory-leak guarantee is made.

## Offline and privacy boundaries

The educational app and imported data can operate without internet after assets are loaded. A locally served static bundle requires only the local server and browser. No service worker or persistent offline cache is installed; a cold remote visit/reload requires its code assets. Imported files are intentionally not restored after reload. No external fonts, textures, analytics or APIs are needed for the application.

## Rights, attribution and release scope

This package includes original code and original illustrative formulas, not raw JPL responses, observational vectors, normalized ephemerides, compact historical payloads, private scientific evidence or a hosted authentic reconstruction. The fixed historical digest is pure integrity metadata; it contains no state vectors or private contact information. NASA/JPL data licensing is separate from Apache-2.0 original code. JPL output redistribution/hosting remains unresolved for the separate data-bearing product. General media guidance and API access are not treated as blanket data licenses. No NASA/JPL sponsorship or endorsement.

Third-party dependencies retain their licenses in THIRD_PARTY_NOTICES.md and installed package distributions. Procedural graphics are illustrative, not verified geography or asteroid shape. Future public deployment, GitHub changes, data redistribution and outreach require separate owner authorization. This candidate is prepared for owner approval; no deployment is included.

## v0.2.0 validation and measured limitations

The preserved private historical validation passed 112 scientific tests, 240 client/Python comparisons and two deterministic network-blocked reproductions. The public clean-extraction suite passed 59 Python tests and explicitly skipped 53 historical-data tests. Frontend data-independent tests passed 8 cases, with one authentic-fixture group skipped; a separate private-fixture campaign passed 39 cases. Actual Windows Chrome browser testing passed 17 workflows plus six final packaged-application checks. These evidence classes are distinct; private datasets and reports are not included.

In a 604.157-second, 294-sample Windows Chrome 156 headless campaign (1280×1000, Intel UHD D3D11), matched blank-browser median working set was 496.60 MiB; educational 2D median was 562.13 MiB, educational 3D playback median 609.84 MiB, and total observed peak 771.35 MiB. The original approximately 400 MiB total-browser target remains **UNMET**, not waived or replaced. Summed process working sets include shared pages and are not unique physical allocation or VRAM. This finite observation is not a zero-leak or universal-device guarantee. See [release notes](RELEASE_NOTES.md) and [changelog](CHANGELOG.md). Data-bearing application redistribution remains unresolved; no complete authentic-data application is publicly hosted by this release.
