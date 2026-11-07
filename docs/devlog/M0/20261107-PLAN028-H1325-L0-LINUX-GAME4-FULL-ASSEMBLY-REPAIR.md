# PLAN028 H1325 — L0 Linux tagged Game4 compile root and exact source staging

[H1324 L0 targeted Action42374747715](https://github.com/lly8666/wbd-next/actions/runs/42374747715) **FAIL** before a test starts, source `f7a12dce54d803de1ee8ae51a9b73f2653c536de`. Actual Rust product build and assembly of `admission_v4_game_linux_test.go` pass, but Go compile fails because `V4LinuxGameAuthenticatedLane` and `v4EmbeddedNativeBridge` do not exist in the assembled donor; **=== RUN never occurs** (`NOT_RUN` for the intended protected zero-vs-hot assertion). The base `manifest-plan020-m0.json` installs selected overlays including the test, not the entire Linux Game product Go bridge. The existing mature native Game4 workflow already stages `r0/go_overlay/internal/realityfront` + `internal/v4productcli` non-test Go files and the two pinned original fakeTCP raw-detached Linux sources on top of that same exact assembly.

H1325 changes *only the small L0 workflow's assembly step* to reuse that same full-package source-verified staging, allowing test compilation. Keeps original donor hash, `linux+cgo+both product tags`, original TLS double test intent, actual `=== RUN` / `--- PASS` required; never invents green from a not-compiled test, never runs actual raw/TUN network, and never alters product code. The new source has not run yet. Preserve original H1324 FAIL, H1317/MTU/other blockers, Windows true scoped PASS, and H1323 governance PASS.

```feature-impact
{"kind":"none","ids":[],"reason":"Test workflow-only source-locked assembly correction for pre-execution compile blockage in a previously unverified original Go TLS Game4 L0 regression; production source unchanged."}
```
