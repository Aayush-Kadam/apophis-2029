# Reproduce browser and matched-memory acceptance

The campaign uses a real isolated Chrome process through independently authorized local Playwright automation. It does not invoke or bypass Computer Use. If your testing policy disallows this mechanism, stop; do not convert unit/static results into browser PASS. No JPL requests are made.

Requirements: built web/dist, installed Chrome, Python environment with psutil from requirements.lock, and Playwright 1.62.1. The test tool is separate from application dependencies; its packages/browsers are not redistributed. Install explicitly if necessary (network/cache required):

```powershell
npm install --prefix .b2-test-tools --save-exact playwright@1.62.1
$env:APOPHIS_PLAYWRIGHT_PATH=(Resolve-Path .b2-test-tools/node_modules/playwright).Path
$env:APOPHIS_PYTHON=(Resolve-Path .venv/Scripts/python.exe).Path
# Optional: files remain outside this source/build tree.
$env:APOPHIS_PRIVATE_FIXTURE_DIR='C:\Your private export\frontend-snapshots'
node tools/b2-browser.cjs
```

Use a fresh output directory/profile for every run. APOPHIS_REPORT_DIR may select a report directory outside source; otherwise .b2-test-output/<timestamp> is used and must never be published. APOPHIS_CHROME_PATH can select the installed Chrome executable. Set APOPHIS_SOURCE_ROOT only when testing another exact source extraction. Do not place authentic fixtures inside web/public or the distribution before testing or packaging.

Without private fixtures, authentic import/memory checks explicitly SKIP. With them, files enter only through local File API selection; the loopback server serves web/dist exclusively. Every non-loopback page request is blocked, and app requests are logged separately from the deliberate blocked external control. Test reports/screenshots for authentic mode are PRIVATE.

The single profile progresses through matched blank, educational 2D/3D, imported data (if available), repeated view transitions, scene unmount, prolonged playback/idle and post-cleanup blank. Chrome version, flags, viewport, durations, process roles, WS/private commitment/USS, headroom, main-renderer JS heap and available scene counters are recorded. Sum WS may double-count shared resident pages; private commitment is not resident RAM; USS omits shared pages. GPU VRAM is not measured. Playwright/CDP instrumentation and headless configuration affect overhead and must be kept identical within comparisons.

A three-sample <512 MiB available-RAM guard and a 20-minute monitor limit bound the session. Original approximately400 MiB absolute WS acceptance stays separate and unmet historically. Incremental phase-minus-matched-blank metrics add information and never silently replace the target. Finite sessions cannot prove absence of every leak. Do not mix different browser versions, instrumentation, viewport, data or window states as exact before/after evidence.

Offline checks distinguish already-loaded code running with browser network disabled from a locally served bundle that needs no internet. No persistent service worker/offline cache is installed; a cold remote reload still needs code assets. The campaign restores networking and reloads to test recovery. No deployment is performed.
