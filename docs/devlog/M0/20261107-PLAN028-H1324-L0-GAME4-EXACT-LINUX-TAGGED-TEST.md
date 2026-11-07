# PLAN028 H1324 — single native Linux deterministic cold authority test

H1323 [governance 42374447411](https://github.com/lly8666/wbd-next/actions/runs/42374447411) **PASS**, following correction of evidence `source_sha` without any network redispatch. Source-d01 [WIN-LINUX 42373564637](https://github.com/lly8666/wbd-next/actions/runs/42373564637) **PASS**, Windows original WAL Fixed/Auto real signed Wintun and non-FEC Rust build qualification preserved.

The H1321 Linux-only `TestPLAN028Game4ProtectedEpochZeroWholeGroupVsSingleLane` was extracted to avoid Windows Go test compile failure, but the existing L1 actions do not show the test executed under its `linux && cgo && wbd_v4_embedded_go && wbd_v4_fec2_product` conditions. Do **not** count the Windows compile PASS as this cold authority test.

H1324 creates one workflow with only one deterministic test. It assembles **same original pinned** Go donor `a7a82db31fe736ffedee330795a3234d358f1984` + exact HEAD overlay under `manifest-plan020-m0.json`, confirms staged tagged fixture bytes match, builds native Linux product Rust library once, then invokes exactly the test with both product tags and demands `=== RUN`, `--- PASS`, and real Go test process exit success. Test verifies original TLS returned identical server epoch can represent two different *protected request intents* (zero→full 4-lane group, explicit old epoch→one hot lane) and rejects an unverified request. It does not use real OS network, so no network performance/MTU/Stop qualification is claimed. Before running, status **NOT_RUN**, after run derive from action only.

Current genuine x86 Game4 overlap artifact positive but Action **CI FAIL** because optional raw M4 proof markers were not copied from ephemeral native client logs; preserve their `NOT_VERIFIED` and no report-only real network rerun. H998 original MTU and L2/L3/physical remain OPEN.

```feature-impact
{"kind":"none","ids":[],"reason":"One source-locked test-only native Linux x86 L0 action for existing frozen protected Game4 requested-epoch authority contract; no product code or new protocol."}
```
