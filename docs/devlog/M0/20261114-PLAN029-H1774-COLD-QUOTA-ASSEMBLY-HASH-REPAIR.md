# PLAN029 H1774 | exact Go overlay assembly hash repair

- H1772 source `a4e0a485` automated Actions: [43535292802](https://github.com/lly8666/wbd-next/actions/runs/43535292802) first failed `assembly blob mismatch: ...m0_native_v4_dispatch_windows.go`; [43535292632](https://github.com/lly8666/wbd-next/actions/runs/43535292632) stopped cheap before real network; [43535292533](https://github.com/lly8666/wbd-next/actions/runs/43535292533) compiled Rust then stopped at the same assembly hash. **FAIL / source preflight**, not a new transport regression.
- H1773 [43535821522](https://github.com/lly8666/wbd-next/actions/runs/43535821522) governance and feature catalog **PASS** after exact evidence/source and card-size corrections.
- Change ONLY three `result_blob` SHA values in `r0/go_overlay/assembly/manifest-plan020-m0.json` corresponding to H1772 DirectFlowHard Go source/Go tests. Original-Go source revision, original blobs and every other overlay operation remain untouched.
- New SOURCE Windows build/runtime and small-cap pressure: **NOT_RUN** after repair. H1771 physical Direct/Tunnel and owned Stop stay a previous-SOURCE scoped PASS; independent `RootCAs` original-Go ABI remains OPEN.

```feature-impact
{"kind":"none","ids":[],"reason":"Source-locked overlay assembly manifest repair only; H1772 cold cap feature semantics and card were already documented, without a new product behavior."}
```
