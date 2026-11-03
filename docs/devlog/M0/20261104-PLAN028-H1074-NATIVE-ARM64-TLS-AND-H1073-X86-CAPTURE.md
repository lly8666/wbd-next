# PLAN028 H1074 — H1073 x86 真 TCP 首载荷证据已收，下一 Linux 任务原生 ARM64 双端

[H1073 Action 41697925602](https://github.com/lly8666/wbd-next/actions/runs/41697925602) SUCCESS。独立下载并核对 artifact `13262935935`（四文件及逐项 SHA256）；使用 H1071 完全相同二进制 SOURCE `d7bd355389c1233c54eaa6a4553ebadcbe0eeb70`，原 Go donor `a7a82db31fe736ffedee330795a3234d358f1984`，Linux x86_64 客户端和服务端各真实 netns、原FakeTCP 443、原Rust TUN、离线预共享随机32B route-key、导入应用专属 CA 与TLS内账号密码。SLL2 `tcpdump -i any` 双视角抓包；临时 pcap 随场景销毁，只留带hash的 TCP 重组 JSON：客户端首载荷 ClientHello record 667B，服务端首载荷 ServerHello record 127B；提前server application bytes=0，兼容SessionID=32B，TLS1.3 keyshare/versions 扩展存在。真实内层 UDP echo 5/5、server Rust shared TUN routed5/stop reader joined 均成功。按契约仅为 x86 Normal first-flight 外观 **PASS_SCOPED**，不是全TLS消息序列/网站指纹/其它模式、Windows/ARM或切网同级PASS。证据 `docs/evidence/M0/PLAN028-H1074-H1073-FROZEN-SOURCED7BD-X86-TLS-FIRSTFLIGHT-20261104.json`。

本轮只有新增**一个原生 ARM64 双端完整 Linux 任务**：[工作流](../../../../.github/workflows/m0-plan028-tls-native-arm64.yml) 运行于 `ubuntu-24.04-arm`，双方都是原生ARM64（不是QEMU也不是异构客户端服务端）。同一 pinned 原Go donor + 本仓库 SOURCE manifest 一次构建 Go TLS/Rust native，ELF 183+SHA256 manifest，有限原TLS测试（Game四lane SessionID、缺key本地拒绝、错key/CA/密码拒绝），然后真实两 netns ClientHello/ServerHello TCP双向重组、5 UDP和精确Stop。未产出 Action 前为 `SOURCE_CANDIDATE_NOT_RUN`，不把旧 WB-R1 ARM64 Native PASS 外推。

按用户平台轮换，本次完整 Linux 任务为ARM64/ARM64，下一独立 Linux 任务应 x86_64/x86_64；Windows 工作不占轮换。H998在线 MTU 热缩旧 FAIL、ARM64 Game4FEC旧 FAIL、远端 ICMP/CPU因果和Windows物理切网未验原样保留。不重写 TLS Persona/FFI/稳态FEC，也不启动旧弱网矩阵。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1074 collect exact H1073 native x86 real two-vantage TCP first ClientHello/ServerHello source-d7bd PASS evidence, then one homogeneous native ARM64 client+server TLS first-flight source-locked Action pending."}
```
