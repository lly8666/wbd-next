# PLAN029 H1983｜收 H1982 原始构建失败，只修精确装配指纹

- H1982 SOURCE `3d0d020ece638ed8eeca4c376408d2e6a883341a` 原 [M0 push Action43824831603](https://github.com/lly8666/wbd-next/actions/runs/43824831603) **FAIL**：cheap job133156071319 第57步 `prepare_windows_wiring.py --check-only` 第一异常 `assembly blob mismatch: r0/go_overlay/internal/windowsclient/native_product_entry_windows.go`；Windows Go 编译和所有原生网络场景均 **SKIPPED/NOT_RUN**，不能给新三条 Defender 孤儿侧证测试贴PASS。原 [H1661 Action43824831641](https://github.com/lly8666/wbd-next/actions/runs/43824831641) Windows job133156070386 同一 SHA 第一失败、无编译。治理 [43824831591](https://github.com/lly8666/wbd-next/actions/runs/43824831591) Feature catalog/Governance 双 job SUCCESS。三个原结果都保留。
- 依 `tools/prepare_windows_wiring.py:MANIFEST` 只改当前生产使用的 `r0/go_overlay/assembly/manifest-plan020-m0.json` 六个 `kind=create` 精确 `result_blob`：H1982 修改的 `native_product_entry_windows.go` / 测试、`native_product_status_windows.go` / 测试、`native_plan029_no_wfp_assembly_windows.go`、`native_plan029_defender_lease_windows_test.go`。旧 exact Go donor SHA、源 overlay 文件 bytes、其余 133 个操作、冻结旧 `assembly/manifest.json` 均原封不动。
- H1983 SOURCE 新 build / Windows Go 回归 **NOT_RUN**，用原 push preflight 自动收件，不重派任何 D/P native 场景。修复不是联网能力PASS；仅冷启动 orphan Defender 独立 sidecar 报告/拒绝/保留，实际 Windows Firewall COM crash restore 仍需要真实 D5 代表验证；H1978 原 native FAIL、H1974 61ms/P2、GUI真实 Connect/Stop、Game4 CN、IPv6、压力/填充继续 OPEN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Collect H1982 source-locked exact manifest failures and update only six changed Go overlay create result_blob SHAs in current PLAN020 M0 manifest; no new network dispatch or product semantic change."}
```
