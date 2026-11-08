# PLAN028 H1423：一次审核完整正式SOURCE装配，补唯一未钉的Go客户端/服务器共用运行时

2026-11-09。[H1422 Action42502316840](https://github.com/lly8666/wbd-next/actions/runs/42502316840) 的原 FakeTCP 7核文件与必要 `m0_install_public_faketcp.py --check-only` 都 PASS，随后 `prepare_windows_wiring.py --check-only` 正确强制失败：`assembly blob mismatch: r0/go_overlay/internal/v4productcli/linux.go`。严格验收按原始 CI FAIL 保留，原生 Windows/Linux TLS/Rust 网络 **NOT_RUN**。

不是再改产品。对 GitHub SOURCE `b1023f909f1eb3e19a986df313e2373fa815faff` 的完整 Git tree 4318 条，和本轮正式 `r0/go_overlay/assembly/manifest-plan020-m0.json` **102 个 overlay_path** 做批量逐文件 blob SHA 比对，唯一失败 `internal/v4productcli/linux.go`（旧锁 `6e905c2a23fc212f3344787a1ba992c9b49e6228`，当前精确 blob `95df7528f02d7c03a675fa98c7ba94a4d16a968f`）。本提交仅更新当前正式 manifest 的这一个 `result_blob`；`original_blob` donor 权限和全文件校验不变，绝不放行任意不符源码。仓库旧 `manifest.json` 是历史快照仍有5个以前就不一致的旧特性文件，不属于这次真实 CI 路径，故不为漂亮日志大幅改历史。H1421 persona 每会话冷接线、Rust严格TTL、AEAD/PN、FEC、用户MTU及原 Windows WAL均不动。

新源码 Go 单测与一场真实跨OS original session业务执行后才可给 PASS；已经完成 Windows A 264/264 与 Linux B 3/236 原失败保留。

```feature-impact
{"kind":"none","ids":[],"reason":"One exact current production Go overlay result SHA pin after exhaustive tree-vs-manifest audit. No product source, wire, FEC or runtime behavior changed."}
```
