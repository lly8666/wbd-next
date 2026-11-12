# PLAN029 H1683｜冻结M4的PLAN029 live product 派生测试合同

- H1682 SOURCE `596a49d480e22c5d128fabebc705cbdd0a306203` [governance-maintenance Action43233940407](https://github.com/lly8666/wbd-next/actions/runs/43233940407) FAIL only at `test_m4_frozen_windows_main_import.test_original_go_manifest_and_guard_remain_exact`: old `manifest.json` created `native_product_entry_windows.go` / `native_product_status_windows.go` SHA retained correctly as 27e3d2 / 83452b; assertion incorrectly compared live MAIN source against those unmodified old M4 hashes while H1682 had independently declared exact live SHA 226e4 / 58c0f in `M0_PLAN029_REVIEWED_CURRENT`.
- Keep M4 PINNED_FILES and original `manifest.json` *unchanged*. Only when path is one of these two explicitly reviewed product files require the PLAN020 current live manifest create `result_blob` and actual repository content to match the independently pinned new SHA; independently assert frozen manifest original remains equal to original M4 PINNED_FILES. No general bypass or new allowlist for arbitrary changes.
- H1681 [Windows Go source+4 pure v2 WAL tests 43233031946](https://github.com/lly8666/wbd-next/actions/runs/43233031946) SUCCESS scoped; H1682 governance [43233940592](https://github.com/lly8666/wbd-next/actions/runs/43233940592) SUCCESS. GUI Action43233031857 still FAIL due to old pinned Rust DLL source mismatch; no silent ABI override. Signed Wintun H1672 no-SYNACK failure retained.
- This batch only corrects obsolete old-M4-vs-live SHA fixture. The v2 OS lease/MTU/DNS/routes product work is still OPEN. No performance/networld claim.

```feature-impact
{"kind":"updated","ids":["windows-network-wal"],"reason":"Align historical M4 manifest test with explicit exact PLAN029 live adapter SHA without changing frozen original data."}
```
