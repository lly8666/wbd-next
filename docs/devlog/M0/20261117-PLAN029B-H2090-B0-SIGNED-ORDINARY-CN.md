# PLAN029B H2090｜签名B0受管DNS成功，单独验证普通CN真实A的路由

H2089 `SOURCE=d0dd9f1bcd662360473a8269effa413369875fb7` [Action44056378053](https://github.com/lly8666/wbd-next/actions/runs/44056378053)、job133949818062、原签名附件14316613440已核：Win2025真正Wintun/Npcap/原Go TLS+Rust与WSL2原TUN及真实双方内核UDP/TCP成功。受管原Winsock **UDP A/TCP A**均从Linux原TUN真实53 socket取203.0.113.77/TTL2，**UDP AAAA/TCP AAAA**均本地NOERROR/NODATA并核Linux上游AAAA次数**0**；business split OFF无Direct NAT/Fake写者，原TLS/OS Applied/Stop/WAL均通过。限为`PASS_SCOPED_B0`；其余B2–B5不借此自称成功。

H2090接下来只启动一场**独立源锁Normal、用户默认外层1460B** [plan029b-b2-cn-ordinary-real]：全新的`cn-domain-direct=false`而`split-enable=true`且`bypass-lan-cn`；Linux外口真实UDP53给CN域名 CNAME→海外A/TTL2，原Linux TUN UDP53给非CN相同203.0.113.77/TTL2。Windows两类原Winsock应用必须各按正确DNS egress还原真实A，且同一海外IP的两条真UDP业务都走原Rust Tunnel，原Linux TUN UDP46113确收到并回传；不能造FakeIP或物理Direct business socket。原已有TLS签名驱动、内核双向TCP/UDP和独立owned Stop全保留；日志来源采用现有allowlist有界脱敏，不携带credential。原H2077高级FakeIP fixture显式新布尔值和原冷日志名在本次同步矫正，不改变产品数据面或TLS/WAL。

H2089治理 [44056377686](https://github.com/lly8666/wbd-next/actions/runs/44056377686) 的独立结构FAIL来自**固定hot read set**（AGENTS/章程/项目/registry/START_HERE/功能目录/M0提示/cursor）实际33141B>32768B；不是M0.context_refs。只将过时的`START_HERE.md`更新成短当前导航，预计固定热集减少800B，无需放宽policy/删除旧证据。原H2083 DLL无V3导出FAIL保持。

**新 H2090 未测**：B2物理结果、独立高级FakeIP、实际IPv6受管帧、GUI真迁移、B5同VM性能不能在此源码候选里标PASS。对准新SOURCE首个实测失败处理，不重跑028/030旧矩阵。

```feature-impact
{"kind":"none","ids":[],"reason":"H2090 source-locked signed B2 ordinary CN real DNS/data fixture and updated START_HERE/previous advanced log oracle only; real product Go/Rust features not changed"}
```
