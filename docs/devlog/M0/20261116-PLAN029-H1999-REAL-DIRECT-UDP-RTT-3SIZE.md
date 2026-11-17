# PLAN029 H1999｜真实 Windows Direct UDP vs 物理socket，96/512/1200B p99
- 用户要求跑多种普通 Direct 工况；H1997同机2048×1KiB已建连 TCP p99 Action43855958211 **SUCCESS**，物理0.410/Direct0.699ms、max0.649/0.878ms。H1998原4MiB无人工pace已在途，另一个独立Action、独立SOURCE。
- 本轮只扩展 H1745 原生签名 Windows CN DNS/FakeIP＋WSL2 独立 Linux Kernel UDP46111 的**纯测试Python**：DNS/单回包验证后，以真实物理源IP绑定 Windows UDP socket 与原Wintun lease→Rust Direct FakeIP UDP 每包120条，分别96、512、1200B，共720个一发一收真实包；每条必须完整回包、原FakeIP/物理来源正确，guest验证物理underlay与序列唯一。没有新Go/Rust/协议/OS guard。
- Windows同一单调时钟报告 p50/p95/p99/max与≥8ms计数。将 `WBD_PLAN029_DIRECT_UDP_RTT_SCENE` 只按 `[plan029-h1999-direct-udp-rtt]` 打开，原 `[plan029-v3-real-direct-udp]` 走正常真实Source。默认其余Action走旧H1745单包行为。DNS/Stop严格门不放宽。
- 本次源签名 Windows原生/三组 UDP p99 **NOT_RUN**，保留H1997证据与所有旧失败；若失败查首个真实socket、Wintun、guest边界，不能绕过超时/失包。
```feature-impact
{"kind":"none","ids":[],"reason":"H1999 adds only signed ordinary three-size physical-vs-FakeIP Direct UDP RTT samples to existing H1745 original test; no product or extreme-condition functionality."}
```
