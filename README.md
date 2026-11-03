# APOPHIS 2029

**A source-available scientific reconstruction of Apophis’s April 2029 Earth encounter.**

Apache-2.0 original code · Python science engine · React / Three.js visualization · Source release candidate v0.1.0-source

## The encounter

This project reconstructs geocentric position, velocity and closest approach using official JPL Horizons vectors, with CAD and SBDB checks. The supported orbit solution is **220**. The reconstructed nominal trajectory is a safe flyby, not an impact prediction. This engineering tool does not provide planetary-defense decisions or a new orbit determination.

## Implemented

- Two-part TDB epochs, cubic Hermite position and velocity interpolation, and a bounded closest-approach solver.
- Independent holdouts, analytic solver checks, temporal convergence and source/hash verification.
- Interactive 3D playback, four cameras, evidence panels, quality controls and 2D context-loss fallback.
- Sequential official API acquisition with user-supplied contact details and a Windows local-server launcher.

## Validation and limitations

Preserved private validation passed **112 Python tests**, including 103 existing tests and nine acquisition guards. The public package includes the test code but excludes historical data and reports. Its documented data-independent subset has 36 tests. Prior client/Python comparisons covered 240 epochs. These are recorded historical results, not a claim that this archive contains the reference datasets or a hosted demo.

Frozen acceptance configuration is in `data/acceptance.json`. It includes holdout position 0.002 km and velocity 0.00002 km/s limits; CAD comparison uses 10 km, 10 s and 0.01 km/s limits. Detailed source-derived numerical result tables remain private pending redistribution clarification.

A previous clean scientific run peaked at 107.133 MiB and took 0.667 seconds wall time on the validation host; this is not a portable performance guarantee. Browser summed working set peaked at 874.746 MiB in the latest 30-minute diagnostic session. The approximately 400 MiB target remains unmet. The latest offline browser-control verification was incomplete. Full data-bearing release status remains **PARTIAL**.

## Architecture

```text
Official JPL APIs -> raw response/provenance -> validated snapshot
                                              |
                                  Python interpolation / solver
                                              |
                                  local compact trajectory export
                                              |
                                  React + Three.js application
```

No browser makes JPL API requests. API source and policy: [SSD APIs](https://ssd-api.jpl.nasa.gov/), [Horizons](https://ssd.jpl.nasa.gov/horizons/), [CAD](https://ssd-api.jpl.nasa.gov/doc/cad.html), [SBDB](https://ssd-api.jpl.nasa.gov/doc/sbdb.html).

# Source-only APOPHIS 2029 candidate

Original owned code is Apache-2.0, Copyright 2026 Aayush Kadam. See LICENSE, NOTICE and THIRD_PARTY_NOTICES.md. This source candidate contains no cached JPL API responses, normalized vectors, calculated encounter datasets, frontend trajectory payload, screenshots or historical data-bearing reports. It is not a ready-to-run offline application or an approved public hosted website. Nothing has been published.

## Prerequisites and setup on Windows

Use Python 3.12, Node 24 and pnpm 11.25.0. Install dependencies from the exact locks; do not upgrade them to make a failed check pass. Open PowerShell in the extracted source folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
cd web
pnpm install --frozen-lockfile
cd ..
```

Dependency installation requires network access or matching cached packages. Installed dependencies retain their separate licenses and are not bundled in this archive.

## Acquire a new private dataset from official APIs

Read the current policy at https://ssd-api.jpl.nasa.gov/ first. Supply your own valid contact email or public HTTPS contact URL at the non-echoing prompt. No contact is invented or saved in the archive or generated provenance. The tool makes five sequential necessary requests, uses one attempt per query with no automatic retries and explicit version checks, saves authentic raw bytes and request metadata, and refuses an existing output directory. Do not run it concurrently or repeatedly for unchanged data.

```powershell
.\.venv\Scripts\python.exe tools/source_release.py --output ..\apophis-api-run
```

The output must be a NEW directory outside the source tree. This workflow reuses the original scientific interpolation, time precision, solver and frozen acceptance limits, redirecting only input/output paths. It checks the full request/cadence/frame/units/provenance contract, matching source solutions and all original numerical acceptance conditions before exporting. The existing application supports orbit solution 220 only; a changed solution fails closed and needs new validation, not edited reference values. A new retrieval is explicitly identified as `source-api-<UTC timestamp>`. The exporter's historical snapshot label is replaced only in the newly generated metadata and manifest, never in scientific vector values or source snapshots.

API availability and restoration of historical orbit 220 cannot be guaranteed. A successful new acquisition is not a grant to redistribute the response, normalized vectors, derived data or built website. Those generated outputs stay private pending clarification. No API calls are made by the browser.

## Build the application from your locally acquired data

After PASS_NEW_RUN, copy the two generated files into the previously empty frontend data folder:

```powershell
New-Item -ItemType Directory -Force web\public\snapshots
Copy-Item ..\apophis-api-run\frontend-snapshots\*.json web\public\snapshots\
cd web
pnpm run test:science
pnpm run build
cd ..
Copy-Item launchers\windows\* web\dist\
py -3 .\web\dist\launch_apophis.py --no-browser --port 8765
```

Open http://127.0.0.1:8765/ and keep the server terminal open. Stop it with Ctrl+C. All playback assets are then local; reload still needs the local server. The helper serves its own directory, independent of the terminal folder. Do not open index.html as file://, and do not serve the outer source directory.

## Tests and historical reproducibility boundary

The mathematical solver, launcher and source-workflow guard tests need no JPL response:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_solver_analytic.py tests/test_windows_launcher.py tests/test_source_release.py -q
```

All original test source is retained unchanged. The historical integration tests include comparisons with the original rejected timestamp-precision result, frozen snapshot and byte-identical historical exports. Those reference artifacts are intentionally absent here. Without the authentic historical baseline, the complete public test collection reports 59 passes and 53 explicit skips, not 112 validated tests. Do not treat skipped historical checks as proof of acceptance on a live replacement. The new acquisition tool independently runs the unchanged scientific acceptance checks against the newly retrieved five-source dataset; it does not fabricate old reports or replace historical regression fixtures.

Exact offline reproduction of the historical gate requires the preserved private baseline. Removing its data changes the distribution contract and is not equivalent to the original offline release. Permission to bundle raw data versus normalized/derived/frontend data and pure provenance remains a distinct owner decision requiring documented terms or JPL clarification.

Detailed R0-R2 evidence and full original numerical reports remain private, outside this source-only package. This README describes the workflow; it does not itself assert that network acquisition was completed or approved for public distribution.


## License and distribution boundary

Copyright 2026 Aayush Kadam. Original owned code is Apache-2.0; see LICENSE and NOTICE. Dependencies retain their own terms in THIRD_PARTY_NOTICES.md. No images, textures, fonts, dependency binaries, JPL responses, normalized vectors, generated bundles or private evidence are distributed here. Acquisition does not confer redistribution permission. A locally generated website is not approved for public hosting by this source release.

## Future work

Possible work includes broader validated orbit support and browser resource improvements. These are proposals, not implemented capabilities.

## Explicit public test tiers

See [TESTING.md](TESTING.md). Run `python -m pytest -q`: 59 data-independent tests run, while 53 historical integrations explicitly skip when the authentic historical baseline is absent. A skip is not scientific validation. The narrower 36-test command selects only three modules; additional data-independent tests are available across the other modules.
