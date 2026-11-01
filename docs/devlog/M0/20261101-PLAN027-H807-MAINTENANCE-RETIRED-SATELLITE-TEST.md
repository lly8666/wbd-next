# H807 — update exact maintenance receiver test after retiring satellite GameFEC Actions

H803 original Windows signed NPF/Wintun ↔ WSL2 Linux Game2FEC6 source21ae Action41323048788 native SUCCESS, actual 43-file ZIP inspected. H804 removed 23 one-off/relay receiver workflow YAMLs and disabled external stages, preserved canonical original real native test+actual full artifact and single independent deadline. H806 cheap preflight no longer fails stale `GameFecRelay` source assertion and performance native [41325559876](https://github.com/lly8666/wbd-next/actions/runs/41325559876) progressing through original Go/Rust build for bilateral 10Mbps/75ms/15loss20s, NO performance verdict yet.

Actual [governance-maintenance Action41325549354](https://github.com/lly8666/wbd-next/actions/runs/41325549354) **FAIL** precisely one outdated `tests/test_m0_wl_gamefec_progress.py::test_h740_independent_receiver_accepts_numeric_supervisor_stages`: it attempted to read deleted `.github/workflows/m0-plan027-gamefec-rescue-record.yml`, raising `FileNotFoundError`. Do not resurrect that separate action just for a test. Instead test that the deleted satellite path is absent, the one independent deadline workflow remains, and `GameFecRelay` source-local numeric supervisor event normalization remains deterministic via injected test-only sender. Original product and FEC bitstream remain untouched, no new API/offline test gates bypassed. This ensures maintenance regression covers the lean architecture rather than the obsolete fanout.

```feature-impact
{"kind":"none","ids":[],"reason":"Update stale governance maintenance test after retiring an obsolete satellite GameFEC workflow, retaining meaningful local numeric marker and independent watchdog expectations; product unchanged."}
```
