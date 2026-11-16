# PLAN029 H1986｜收 H1985 原 Windows 三项 PASS、维护 M4 旧SHA 8 FAIL

- 原 H1985 SOURCE `8a43e84e857b1156407a403220a7f468c8bbce72` 的 [H1661 Action43827317944](https://github.com/lly8666/wbd-next/actions/runs/43827317944) Win2025 job133164118238 **SUCCESS**：真正执行 `TestPlan029NoWFPAssemblyRejectsUnreconciledDefenderSidecar`、`TestPLAN010NativeReadOnlyDiskStatusAndConflict`、`TestPLAN010OriginalNativeRecoveryNoShellOrLegacyFallback` **各PASS**，Go 源码构建 PASS，单个精确 owned Defender COM Add/readback/CAS/delete **PASS_SCOPE_ONLY**。没有实际产品 Direct TCP/UDP 网络、完全 D5 中断恢复仍 NOT_RUN。 [governance43827317992](https://github.com/lly8666/wbd-next/actions/runs/43827317992) SUCCESS。
- [H1985 原维护Action43827317993](https://github.com/lly8666/wbd-next/actions/runs/43827317993) **FAIL**：job133164118981 在 745项静态套件中 8次精确旧哈希断言失败；都来自 `test_m4_frozen_windows_main_import.M4FrozenOverlay`：本轮 H1982 新增合法 PLAN029 巡检/恢复逻辑修改的 `native_product_entry_windows.go`、`native_product_entry_windows_test.go`、`native_product_status_windows.go`、`native_product_status_windows_test.go` 在生产 `manifest-plan020-m0.json` 已用六处真实 SHA 锁定，但独立旧M4测试的 M0 reviewed SHA map 仍是旧值。**并非**原 M4 donor/冻结 manifest 被改，也不恢复旧网络矩阵或放松校验。
- 本批只更新 `tests/test_m4_frozen_windows_main_import.py` 的 `M0_PLAN029_REVIEWED_CURRENT` 四条精确当前 Git blob SHA，并将 entry/status 两份测试加入明示 whitelist；保留 `M4_FROZEN`、`PINNED_FILES`、`manifest.json`、真实生产 manifest 和原样 SHA 严格比较不变。新的测试/治理/实网在提交时 NOT_RUN，保留 H1985 原 Action 红灯。
- H1978原 native FAIL、H1974五次61ms、GUI实际按钮、Game4 CN接线、D1–D5/P1–P2、IPv6/压力/填充仍OPEN，不报告029交付。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1986 collect actual H1985 source-locked Windows 3 pure orphan Defender tests/owned single rule CAS PASS, and keep 8 historic M4 SHA failures; align only four exact M0 reviewed hashes and strict allowlist with source-locked live PLAN020 manifest."}
```
