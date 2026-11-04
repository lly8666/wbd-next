# PLAN028 H1101｜最新 ARM Game2 收证，x86 Game4 末端标记修复，Fixed/Auto 同 SOURCE 并行

最新 SOURCE `0e47d9c9532cbda9e655bd198348acf4ff4ddcd1` 已在原生 ARM64/ARM64 的 [Action 41782228907](https://github.com/lly8666/wbd-next/actions/runs/41782228907) **SUCCESS**：每代两条原 Go FakeTCP/TLS lane，真实 kernel tcpdump 重组 4 个 ClientHello，首次有效载荷标准 TLS、未见 WB-R1，server 无提前数据。OS 出口源IP `10.25.0.2→10.25.0.3`；新 TLS/Rust group 在旧 Stop 之前 READY，旧客户端内层IP续接、原 Rust 单 TUN reader、切网前后各5个真实 UDP Echo、外层1460意图/物理1280下内层 OS 读回1193B均通过。工件 `13299183477` 已独立解包检查 manifest、原生日志和 wire JSON hash。

x86/x86 的 [Action 41782228876](https://github.com/lly8666/wbd-next/actions/runs/41782228876) 仍为 **FAIL**，工件 `13299199278` 却有真实 Game4 fixed6 的 A→A+B→B、8个真实 ClientHello/无前导、5+5 UDP、单 TUN reader、两代 parity copied、new MTU1178B。工作流最后比较了不存在的 `...GAME4_EIGHT_REAL...`，而业务脚本实际发出的是 `...GAME4_8_REAL...`。因此仅修这个字符串和下一次源码变化时的工作流入口，不为测试拼写刷第二遍 Game4 SOURCE。保留 Action FAIL 不伪造绿色。

**下一个完整 Linux 任务：x86_64 客户端＋x86_64 服务端。** 原生 Fixed 与 Auto 的实际出口切换尚需新 SOURCE 场景，选两条**独立并行 Actions**。直接下载上面 H1100 x86 工件中的 Go client/server 和 Rust so，逐 SHA256、ELF 架构和 SOURCE 校验，不重编。仅在 runner 中用小型 `m0-plan028-normal-fec-path-fixture.py` 基于现有真 netns 原脚本生成临时副本：开放 `fec-fixed`/`fec-auto` auto-IP 换路径，旧阶段64真实 UDP + 新阶段5真实 UDP，保持源IP变化、前后 TLS、owner Stop、受保护 /32、物理MTU1280下OS TUN读回、FEC Readback/PENDING 不夸大 Auto 成熟度。不给原脚本永久复制一套，也不触发旧 28min PLAN012 大矩阵。

本包只是 checkpoint：Fixed、Auto 的新 Actions **待结果**；Windows 真实物理 NIC、CPU/p99、Android 等未证明。H998在线热缩MTU FAIL、旧ARM Game4FEC Action FAIL、远端ICMP未测照旧。Route-key 32B本地导入、无 WB-R1 与TLS证书验证已在H1087 **限定收口**，不重复测试该独立包。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1101 exact source0e47 ARM Game2 native true overlap PASS, x86 Game4 overlap app/wire observed but Action marker FAIL retained; source-frozen original Go/Rust Normal Fixed and Auto x86 physical-switch tests launched independently."}
```
