# Two-tier verification

Tier A: `python -m pytest -m data_independent -q` runs mathematical, synthetic parser, workflow and launcher tests without observational inputs.
Tier B: `python -m pytest -m authentic_data -q` collects original integration assertions. With no historical raw snapshot they explicitly SKIP (BLOCKED). Supplying a partial or corrupt raw snapshot causes the original checks to run and fail, rather than hiding corruption. Preserve original expected paths and hash manifests. Newly acquired data is not automatically an equivalent historical fixture.
All tests: `python -m pytest -q`.

The private 112/112 baseline includes both tiers with original authentic reference artifacts. A public 59-pass/53-skip run is not equivalent. No tolerances or original test bodies changed. The acquisition wrapper independently verifies a fresh official run but cannot manufacture old reference reports. No data is included here.
