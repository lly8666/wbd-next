# PLAN028 H1556 — fixed original Go assembly source and declared feature impact (2026-11-11)

Following H1555, [x86/ARM64 original-Go assemble Action 42940982220](https://github.com/lly8666/wbd-next/actions/runs/42940982220) first rejected before build: `FEC2_ASSEMBLY_REJECTED: overlay result blob mismatch: internal/realityfront/admission_v4.go`. Same first error in wrong-password Action 42940982196; they do **NOT** evaluate product TLS/data or throughput. Governance passed but feature catalog Action 42940982227 rejected undeclared product delta. These failure Actions are preserved.

This commit changes **only assembly metadata, feature card, evidence, and cursor**; H1555 Go logic is unchanged. Pinned Git blob SHA for modified `admission_v4.go` and `v4productcli/linux.go` now matches SOURCE bytes, and the changed `v4_manual_lease_map_test.go` is included as an actual original-Go `create` operation rather than leaving a decorative but unassembled test. No new source protocol or steady Go worker. H1556 SOURCE must build/test in automatic Actions before any admission claim. Original 19f prebuild is not a network FAIL.

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1555 repairs credential-verified per-account manual roster automatic-IP reply on the existing protected TLS lease field, allowing one manual Windows device and Linux auto rotating devices on the same original TLS443 server. Existing single manual mode, unknown account denial, data plane and wire remain unchanged; Windows real mixed source still NOT_RUN on H1555 after assembly gate."}
```

Feature card `docs/features/entries/tls-auth-multiclient.json` retains all prior exact PASS/FAIL, adds H1555 original failures, and keeps revised authenticated roster-native 600s qualification NOT_RUN. No source hash from current test is silently called PASS. PLAN028 IN_PROGRESS.
