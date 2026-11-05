# PLAN028 H1231 — Game4 真单lane热换（SOURCE 候选）

## 病灶与设计

H1230 七模式浮动定时**整组**换代SOURCE0cda x86/x86已真实PASS（16219/16220）；但过去 Game4 每轮四条 TLS 与单一Rust GameAdapter 重建，不是每条独立热轮换。用户2026-11-05明确要求继续修复。该代码候选要**改变真实产品行为**：

1. Linux 原始 Go 单一 path supervisor 在Game4 unchanged-physical timer due时，不再launch四lane候选，发送一次 lane-turn 到CURRENT client group。18s ±3s重新抽，物理切网仍用先前已验证的整组 A→B。
2. Original Go client以同一通过身份的 epoch，在新的独立源port进行一次真实TLS/FakeTCP、已原有 Rust M1 prepare/commit；server原始443多客户端 TLS 完成后，识别同 principal+tunnel+epoch，拒绝改 FEC/身份，仅替换该 group 的指定 lane；余3条 Go TLS 不重连。
3. Rust new FFI 只在现有原始 Game group 上CAS前任 native handle、检查 M1 新的授权 cold 身份及epoch/lease/四元组，交给**现有** TX/RX lane worker 换新 AEAD/PN、真实 raw RX socket，再精确Stop所选旧 lane。共享 GameTx logical IDs、GameRx dedup、Fixed6 FEC 和唯一 TUN reader 不重启；无 wire、AEAD算法/record/FEC结构改动。
4. 装配不修改默认 IPv4 MTU 1460B。不增加 recovery controller，保留旧源验证；如 native局部失败不报成功，fail closed。
5. 新专用 ARM64 原生 client+server test：Game4 off、Fixed6 两job复用一套 binaries；每job 18±3s **8次逐lane** 1,2,3,4,1,2,3,4，三台客户端连续原生TUN UDP无重试，检查服务端同一 native GameAdapter 初建只一次、新端口逐lane匹配、3条 sibling 不重新认证、8次 M4确认/旧owner Stop、物理NIC/IP/MTU未变；真正 UDP 收发/p99/最大gap记录。NOT_RUN直到 Action/原件证实。

**风险/资格：** Native ABI与Go group生命周期同时改动，尚未编译或原生测试，不冒充已解决。H998同socket在线MTU收窄FAIL、历史ARM Game4 FAIL以及远端ICMP未测保留。H1225 Game2/4 p99旧源PASS仍非本新SOURCE资格。

```feature-impact
{"kind":"updated","ids":["original-lane-rotation-jitter","game-lanes"],"reason":"H1231 user-authorized real independent Game4 same-epoch one-lane TLS/M4 hot swap across existing supervisor and M4 owner; native ARM64 business pending."}
```

## H1233｜ARM64/ARM64 原生 Game4 单 lane 真正自动热换完成

- Exact tested product SOURCE `814dec69f5200fa62dc63b76cb9ded1e9680a9b5`, original pinned Go TLS and Rust M4 native ARM64 binaries in [Action 41986067696](https://github.com/lly8666/wbd-next/actions/runs/41986067696), build plus **Game4 Off and Fixed6 two real business jobs PASS**. Supplementary native ABI run41986067687 PASS.
- Both modes **eight separate original TLS/M4 rekeys per original Game4 group** lane1→2→3→4 twice, 16 selected actual new per-lane source ports matched client/server logs; only initial one Game4 server Rust owner, no 4-lane group re-creation, other 3 TLS sockets keep running. All 16 actual jittered delays 15–21s.
- Three simultaneous authenticated real inner TUN UDP streams without app retries: Off alice1553/1553 bob1552/1552 carol1553/1553, Fixed6 alice1593/1593 bob1592/1592 carol1593/1593, **9436/9436 received** in these native no-injected-loss runs. Bob received-only RTT p99 Off 0.7198ms, Fixed6 0.7281ms; largest successful receipt gap109.502ms. Not a universal zero-loss WAN guarantee.
- Both artifact ZIPs downloaded and upload SHA256 matched, CRC/testzip PASS, 9 files each, original raw 4 runtime logs and 3 actual stream receipts. See `docs/evidence/M0/PLAN028-H1233-SOURCE814-NATIVE-ARM64-GAME4-INDEPENDENT-LANE-HOT-REAL-UDP-PASS-20261105.json`; Go original StopAndRelease called before turn Ready, but no dedicated per-lane kernel stop trace exported.
- Historical H998 true live same-socket MTU shrink FAIL and old ARM Game4 Action FAIL retained, other OS/physical switch/netem 5/30%/remote ICMP/CPU causality NOT_RUN under this exact SOURCE.

```feature-impact
{"kind":"updated","ids":["original-lane-rotation-jitter","game-lanes"],"reason":"H1233 source814 native ARM64 original Go TLS/Rust Game4 truly independent 16 single-lane swaps with 9436/9436 no retry UDP, original verified artifacts and preserved sibling GameAdapter/FEC."}
```
