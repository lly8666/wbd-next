# PLAN028 H1403 | Windows Game4+FEC 原始认证 B 代的 server grace 假失败口径修复

2026-11-08，源 `e69e40f3e6da2236542d4cac9fe060f840f39c43` [原始 Action42483793673](https://github.com/lly8666/wbd-next/actions/runs/42483793673) **原 CI FAIL 保留**。原 Windows2025 真实 Npcap/Wintun 签名驱动＋原 Go TLS 四 lane、Linux WSL2 原生 Rust M4 4/4 接线，一代与真实源IPv4 .1→.9 的二代均认证/OS Applied/Ready。原 Windows 真 kernel UDP 第一代 sent73 unique_rx72，Linux反向 true UDP 同窗口 unique72，原客户端 exact owned Stop+WAL恢复，server 两代真实 auth groups 已就绪。原 Windows Rust DLL / Linux release 链接固定 ISA-L，第二代 server 真实 `M0_GAME_M4_FEC_BACKEND_READBACK native_linked=1 tx_native_quanta=4`，但客户端本次没有同类真实 backend quanta 日志，仍单独记未证。

原试验约 13:23:59 向 server 发布第二代真实授权，server 打印 `V4_PUBLIC_GAME_OLD_SERVER_RETIRE_SCHEDULED ... grace_ms=16297 old_m4_rx_preserved=1`；现行 `r0/go_overlay/internal/v4productcli/game_linux.go` 的真正旧代释放只在 `originalLaneRetirementGrace()` **10–20秒**过去后输出 `V4_PUBLIC_GAME_GROUP_STOP_DRAINED reason=same-protected-cohort-grace-expired`。但原 `tools/m0_wl_public_normal_e2e.py` 在第二代 READY 后立即要求不存在的 `reason=same-protected-cohort-new-generation`，失败并在约7秒即主动关闭 server，日志实际只有 `server-close-during-grace`。该独立的真实 Old Stop 硬门**未触发，不能按新用户口径强判完整场景 PASS**。同时最显眼的 `M0_PLAN027_GAME_DUE_FAULT stage=send_records_entry` 经查 `v4_windows_game_native_runtime.rs` 是 `first_due_entry` 只执行一次的诊断日志，不包含失败 rc；不能只追日志字面把它当真实 TX 故障。

H1403只修测试夹具，不动现行协商、ISA-L、Rust TX/AX、Health/Stop与10–20s原产品参数：先要求第二代 **真双向 inner UDP unique 收件增加**，随后解析同源 server 真 `OLD_SERVER_RETIRE_SCHEDULED` 的实际 `grace_ms` (10–20s) 并有界等待 `grace_ms+5s`，期间禁止 server/client 退出、确保 B UDP 两方向继续增长，最终必须恰好一次原 server `...same-protected-cohort-grace-expired`，在 report 单列前后真实数据与 Stop。新完整场景真实结果**待自动 Action**。原 network/CI FAIL、不触发精确旧 Stop 和其余未跑范围均保留。

```feature-impact
{"kind":"none","ids":[],"reason":"Only real Windows Game4FEC scene test timing and exact existing server retirement marker; no product owner/grace/protocol change."}
```
