# PLAN028 H1406｜Windows原 Game2/4 FEC 在 owned Stop 读回 ISA-L 真实量子

2026-11-08。已验证 [H1405 source d309 真 signed Windows2025/Wintun/NPF Game4+FEC6 ↔ Linux 原TLS443/Rust M4](https://github.com/lly8666/wbd-next/actions/runs/42485343180)：第二代新原 business 在原服务端18.807s旧代 grace 中继续，精确旧代/最终 Stop，双方向真实 UDP/TCP 全部 PASS_SCOPED。两个实际原生二进制用相同 SOURCE，Win Rust MSVC ISA-L fixed官方静态档构建及 native feature通过，Linux server`M0_GAME_M4_FEC_BACKEND_READBACK ... tx_native_quanta=4`，但 Win 客户端未输出实际 ISA-L/native量子，不能把编译证明偷换成运行触发证明。

现行 `crates/wbd-engine/src/v4_windows_game_owner.rs::stopped_group` 已有原 FEC WinGameGroup`adapter.game_fec_counters()`及 RX counter，并在真正原 M4 kernel/Npf reader Stop/quiesce且无 staged/待确认行后才调用 `game.adapter.stop()`。仅在这个**冷 Stop** 一次读取原计数并打印 `M0_WINDOWS_GAME_M4_FEC_BACKEND_READBACK group=... selected=... native_linked=... tx_native_quanta=... tx_scalar_quanta=... rx_native_decodes=...`，绝无热数据轮询/新线程/packet头/Go热泵/算法改变。FEC Off不发readback，k1/短帧合法scalar不算硬件故障。保护既有完整 owned Stop 锁/资源边界，一原 group一次读回。

单项 Win原生Game4FEC带真实 signed Npcap/Wintun、原Go TLS/Rust/双代/source4变化/18.8秒old grace、双向应用与最终 Stop 由当前 workflow自动执行；验证必须看到真实 `native_linked=1`、实际 `tx_native_quanta>0` 才能记 Windows Game FEC 默认native真实触发。若场景只发短块，则仅将触发标 NOT_TRIGGERED，另选长业务大包定向实验，不放宽产品身份/Stop。原先其他平台 L3不为一个冷统计重跑。

```feature-impact
{"kind":"none","ids":[],"reason":"Read already-existing original Windows GameFEC native/scalar counters once at owned Stop; no new product wire/config/steady-state behavior."}
```
