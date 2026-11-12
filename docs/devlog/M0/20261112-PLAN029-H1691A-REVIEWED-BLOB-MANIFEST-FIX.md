# PLAN029 H1691a｜SOURCE manifest 不匹配：实际首次失败点和定向修复

- H1691 `3fe5a94b44f982faf519c947d10369c6f94f5200` 在原 Go 网络代码运行前被两个旧 SOURCE 门正确阻止：[M0-WIN-LINUX 43246325510](https://github.com/lly8666/wbd-next/actions/runs/43246325510) `prepare_windows_wiring.py --check-only` FAIL；[M0-WIN-WAL 43246325426](https://github.com/lly8666/wbd-next/actions/runs/43246325426) 原始 Go + Win32 入口的 Git blob 校验 FAIL，明确首异常 `assembly blob mismatch: r0/go_overlay/internal/windowsclient/native_unified_live_os_receipt_windows.go`。**Windows Go 编译和 v2 新单测未曾开始**，不得写 PASS。
- v2 receipt loop 与新增纯测试两份文件是 H1691 真实 main owner 变更，不属于旧 immutable M4 donor。按实际 Git blob 分别将 manifest `result_blob` 更新为 `bc4020c8bf269111dfad5a2ad8d5a6a2c583fc38` 与 `cb363fb1dc92cf49f61829da490d204cb0380dc8`；保持 donor baseline 和原始 v1 对比引用不变。用同一主分支 SOURCE 构建/验收，绝不改掉严格校验。
- 此修复只恢复可复现来源，若 Go 编译/测试另有错按首个新失败逐一修；no-WFP 四阶段依旧生产 `assemblyOnly=true`，没有真实 Wintun OS Applied，H1690 UDP/TCP kernel ingress FAIL 未恢复。

```feature-impact
{"kind":"updated","ids":["windows-network-wal"],"reason":"Align exact main-owned H1691 receipt/test Git blob hashes in source-locked original Go assembly manifest; preserve original M4 donor baseline and strict mismatch gate."}
```
