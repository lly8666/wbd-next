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
