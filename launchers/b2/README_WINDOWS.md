# APOPHIS 2029 B2 — Windows static launch

Extract the complete ZIP first. The application folder is **APOPHIS_OBSERVATORY**; its entry point is **APOPHIS_OBSERVATORY/index.html**. Keep assets, favicon, notices and launchers together. This is a data-free dual-mode candidate: the educational example runs immediately, while local reconstruction needs your own supported files.

1. Install/use Python 3.9+ and a modern browser. No pip/npm installation is needed to serve this prebuilt bundle.
2. Double-click START_OBSERVATORY.cmd inside APOPHIS_OBSERVATORY, or open PowerShell and run:

```powershell
py -3 "C:\Your extracted folder\APOPHIS_OBSERVATORY\launch_observatory.py" --no-browser --port 8870
```

3. Open http://127.0.0.1:8870/. Keep the server terminal open. Ctrl+C stops it.
4. If the port is occupied, use --port 8871 and the printed URL. The helper serves its own folder independently of terminal location and binds only loopback.

Do not open index.html as file:// or serve the outer extraction directory. The source-only ZIP needs its build steps from the root README before a static app exists. The original launchers/windows scripts describe a different historical data-bearing bundle; use launchers/b2 for B2.

The default banner reads EDUCATIONAL DEMONSTRATION — NOT VERIFIED APOPHIS EPHEMERIDES. Its illustrative values are not JPL measurements. Switch between 2D and 3D, play/pause, scrub time, select cameras, drag to orbit and scroll to zoom in 3D. If WebGL is unavailable, the same selected curve is available in 2D.

To load local science, select manifest.json and encounter.json in the import panel and acknowledge local-read consent. Supported schema 1.0/orbit220 exports are checked for structure, provenance and integrity. An exact reviewed historical byte match is distinguished from compatible but unauthenticated input. No dataset is included, uploaded or persisted. Import does not grant redistribution rights. Clear local data or reload to return to the educational example.

This locally served bundle needs no internet after extraction and Python/browser installation. No persistent offline cache is installed for remote hosting; a cold remote visit would still require code assets. No JPL API, analytics, external font or texture is used by this app.

Original code is Apache-2.0; dependencies retain separate terms in THIRD_PARTY_NOTICES.md. No NASA/JPL sponsorship or impact-prediction authority. The approximately400MiB browser working-set target remains unmet historically; see the separately delivered B2 report for actual measurements and limits. No deployment or publication is authorized by this private candidate.
