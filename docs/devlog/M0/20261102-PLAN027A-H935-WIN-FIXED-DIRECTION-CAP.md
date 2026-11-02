# PLAN027A H935｜源代码定位的 Windows Fixed READY 前 MTU 绑定失败

恢复 `adc18d75354c24103f10cfc5a90bf7d4207690fa` Action `41437214958` 原生 Windows↔WSL 结果：Normal PASS，Fixed original Go TLS 已认证，`requested_tun_mtu=1273`、`client_record_offer=1318`，但 Windows Rust v5 `bind_outer_inner_budget` C ABI rc=1，客户端未 READY。之前简记「READY前失败」不够具体，本次补实际环节。

根因：Rust Windows owner 拿其 **出向** `server_limit` 推 `normal_off_windows_budget`，对比 **本地接收** Wintun `planned_inner` 时没有先用另一方向的 receiver cap 收窄。若 peer 允许较大 record，算出的业务上限高于本地 inner，就拒绝全部启动。修复沿唯一纯 Rust `v4_mtu_budget_ffi::derive_receive`（同一31+14预算）在 v5冷边界组合真实 `outer`、原始 peer MSS、认证 cap、FEC模式、planned inner，得不大于原 peer cap 的新 **TX** record cap；只改Entry冷预算值，不动独立RX admission、不重置PN、不改加密密文/Stop。失败前恢复旧cap，未通过的受限路径仍返回INVALID。独立 literal Golden 增补 FEC outer1500/receiving1273/wire1318/inner1273；普通1460默认不变。

这是已锁定场景根因修复而非全模式证据：H935 新SOURCE Windows Fixed/OS Applied/弱网/性能均 NOT_RUN，旧 `41437214958` FAIL 保留；最新H932/H934 code+governance unit PASS独立记录。

```feature-impact
{"kind":"updated","ids":["path-mtu-budget"],"reason":"Fix authentic Windows Fixed C ABI rc=1 pre-READY by applying pure Rust cold receive-inner record cap to local scoped TX owner before v5 bind, preserving peer authenticated cap and independent RX/OS state."}
```
