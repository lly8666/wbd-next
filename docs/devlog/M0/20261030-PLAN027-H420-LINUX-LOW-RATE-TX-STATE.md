# PLAN027 H420｜Linux bounded low-rate sender core

恢复 main 3efed7c6、M0指令/章程/registry.goal/cursor/PLAN027与精确SOURCE最新 Actions；已有 H419 native-functional/ABI/cross/Windows-Linux preflight/governance SUCCESS，不把它们移植到新SOURCE。

为 Linux 受原 Go TLS 授权的单 Rust M3/M4 Auto owner 实现 1024-PN 有界 sender、最多16个闭合发送历史、经真实驱动F/UNKNOWN状态计数、START先发/CLOSE后发及失败保留、匹配v2成熟摘要和5s slow累计；RX 最多16条认证摘要 inbox，不信 TCP外观ACK。next PN 读取现有M3 allocator，不新建密钥/PN。**本提交先新增状态及结构**，后续接内核收发和Auto读回，不宣称全线完成/测试通过。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Add bounded Linux Auto quality sender and authenticated report-inbox state; production wiring and qualification pending."}
```
