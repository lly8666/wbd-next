# PLAN028 H1042 — Game4 fixed6 双组与同安装 A2 原生候选

H1041 已验证原 Go TLS、同端口/共享 TUN 的 Game2 A→A2+B 和 Game4 A+B，但尚未覆盖 **Game4 fixed6** 两设备重叠及同设备新代接管的真实 FEC kernel 计数。

本次复用同一原生四 netns 夹具与原 Go/Rust SOURCE：Game4 fixed6 在双方显式协商，A/B 两账户不同 /32 与不同安装身份并发真实 UDP；Alice 新原 TLS A2 使用同安装身份、重用原租约 /32，旧 A 精确 Stop，Bob 保持收包。为各组增加 64+ 真实内层 UDP 以激活 FEC2 parity。服务端原有每组 exact Stop 前读取已存在 Rust Game M4 driver source/parity counters，断言旧 A、B、A2 三组各自有 native parity copied；不添加反馈协议、逐包 Go 热工作或新恢复器。

**当前仅 SOURCE 候选（IMPLEMENTED_NOT_TESTED）**。源锁 Action 的真实结果及 manifest 待核后再分类。Windows 真物理切网、真实 90 秒 Game dead-group 自动退休、七模式完整切网、ARM64/公网和 CPU 因果资格均不由该候选证明。旧 H998 在线缩窄 FAIL、ARM64 Game4FEC Action FAIL、远端 ICMP 未测原样保留。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1042 Game4 fixed6 multi-cohort authentic original TLS A+B/A2 and per-group Rust FEC source/parity/driver counters at exact owned Stop; native evidence pending."}
```

## H1042 原生同 SOURCE 结果

SOURCE `58c7d9f2e3dac052e216b117e85ec65cd9c0fc61`，[Action 41646279251](https://github.com/lly8666/wbd-next/actions/runs/41646279251) native job `125952348228` **SUCCESS**。强制检查原GoTLS/Rust Game4 fixed6 A+B、同安装新代A2、真实TUN UDP、Bob业务不因旧A精确Stop中断，以及三组Rust M4 parity kernel copied均大于零。未独立解包核对ZIP的manifest细项，未提供CPU/p99、Windows真实切网、Health90自然退休或ARM64资格。
