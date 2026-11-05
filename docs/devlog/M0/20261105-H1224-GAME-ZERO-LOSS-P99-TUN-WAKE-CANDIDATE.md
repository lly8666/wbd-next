# M0 H1224 — 临时任务：Game 零丢包 p99 高尾延迟

**状态：CODE_CANDIDATE，ARM64 原生 A/B 未运行。**2026-11-05 用户插队新任务。复用 H1223 SOURCEed805 已核证原始 Go TLS + Rust：无 netem、3 个同时独立客户端 100Hz 持续 UDP，Game2 OFF RTT p99=3.739ms、Game4 Fixed6 p99=14.339ms；同场 Normal Auto p99≈1ms。2267/2267 回包，不能用网络重传解释低损高尾。

## 根因与最短收益链

- Rust `crates/wbd-engine/src/v4_game_public_kernel.rs` Game TX worker 由已有唯一进程 TUN reader 将消息通过每 session 有界 `std::sync::mpsc::sync_channel` 分发。但 TX 调用 `try_recv` 后在队列暂空时用 `thread::sleep(2ms)`（Game2 OFF）或 `sleep(1..10ms)`（Game4 CopyStagger/FEC）。业务一旦在睡眠期间到达，不触发唤醒：请求与回包链分别承受额外延迟，零丢包仍出现高 p99。此是**读者→TX worker 通知错配**，不是 FEC 需要等待块完成，也不是增加收发缓冲的理由。
- 修为 TX 用**原同一频道的 `recv_timeout` 等待**，队列来包立即唤醒；把抢先收到的 1 个有归属 packet 暂存，下轮同 owner 跑原 `offer→GameTx→独立 PN/AEAD→native M4`。超时取 Copy/FEC 的最早 deadline，保持原最久 10ms Stop/Health 检查，Server/Client共享读 TUN 仍只一个；无新 FFI、Go 泵、路由头、每包锁或丢包策略。非共享 TUN kernel poll 路径不改。
- 不误改四副本的 `[0,4,50,140]ms` 稳态策略；第一副本仍立即出站，FEC source 原逻辑亦立即提交。先消除被忽略的队列唤醒，再用对照确定是否有剩余高尾。1460B 默认外层完全不变。

## 一次 native ARM64 双端、同 VM A/B

- 2026-11-04 用户 Linux 按**完整任务**交替：H1223 x86/x86 后，H1224 用 **ARM64 client + ARM64 server**，不混搭、不开 QEMU。单次完整 Go TLS/assembly + baseline Rust 和 candidate Rust 两套本机 ELF，build job 只一次、SHA manifest 复用。
- 两个独立并行场景 job Game2 OFF、Game4 Fixed6，各在**同一个 ARM64 runner**顺序跑旧→新。同一个 three-device real TLS + single443 + Rust TUN UDP 夹具，12s 定时换代两次，3 条 100Hz no-app-retry UDP（含同时在线 Normal Auto 对照），观察真实源/IP、Stop、p99/CPU，要求旧新收发完整，目标 Game p99 至少降低 20%，Normal 不能显著回退。没有人造 loss/恢复 probe/跨 VM 因果混比。
- 旧 H998 同 socket live MTU FAIL、历史 ARM Game4 Action FAIL、Windows/Android/远端 ICMP/CPU 因果 NOT_RUN 不变，旧 H1223 PASS 不授给新 SOURCE。原生性能结果前新功能标 NOT_RUN。

```feature-impact
{"kind":"updated","ids":["game-lanes"],"reason":"New user-inserted zero-loss Game p99 tail latency repair changes only original Rust shared TUN TX notification, ARM native same-VM A/B not yet run."}
```

## H1225 — ZERO LOSS Game p99 原生同VM A/B结算

- <https://github.com/lly8666/wbd-next/actions/runs/41964778141> native ARM64 client/server, one Go TLS and two source-specific Rust M4 ELF SHA builds; same runner OLD 40ce34 → NEW 4221e9. Two independent Game jobs, no artificial loss; all 3 clients continuously send genuine 100Hz UDP while authenticated gen1→2→3 and old exact Stops1/2. Both jobs all steps green.
- **Game2 OFF:** RTT received-only p99 **3.027436→0.706066ms (−76.678%)**. Normal sibling 0.832→0.879ms; base 763/763, fixed 792/792 true echoed TUN UDP.
- **Game4 Fixed6:** RTT p99 **18.483483→0.736593ms (−96.015%)**. Normal sibling 0.890→0.787ms; base 758/758, fixed 792/792 true UDP. Preserved mode2 raw copy schedule (0/4/50/140ms), original Fixed6/profile6 FEC and actual M4 owned Stop.
- Across both scenes, base 1521/1521 and candidate 1584/1584 no-app-retry real UDP; all compared sources and 3 devices read back, no DNS/probe/extra packet wire. Two downloaded ZIPs checked against GitHub SHA256, CRC and 13 raw/evidence files each. See `docs/evidence/M0/H1225-SOURCE4221-ARM64-NATIVE-GAME-ZERO-LOSS-P99-QUEUE-WAKE-AB-PASS-20261105.json`.
- This is first-order architectural latency fix: *channel wake, not FEC rewrite*. No extrapolation to 30% impairment, high-load WAN, Windows/Android, remote ICMP, inner TCP, causal CPU benefit, nor old H998 live MTU FAIL. Next whole Linux test returns x86/x86 after this native ARM task.

```feature-impact
{"kind":"updated","ids":["game-lanes"],"reason":"H1225 real native ARM zero-loss source-specific Game2/Game4 shared-TUN channel wake p99 A/B significant improvement with complete UDP/Stop/lease; retain unqualified scenarios."}
```
