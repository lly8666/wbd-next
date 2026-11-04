# PLAN028 H1092 — x86 Game4 overlap + 8 条 TLS 首载荷真实收口

收已在途而不重复派发：SOURCE `67ba10dd7f818a327041e0e5c16e5b69f9f32d0a` [Action41767053797](https://github.com/lly8666/wbd-next/actions/runs/41767053797) SUCCESS。原 Go donor a7a82db + Rust1.85.1 / Go1.23.12 的本SOURCE原生两端 x86_64 netns Game4 fixed6；下载工件13292633595并独立核每个 ELF=62、manifest二进制 SHA256、原Rust fence unit和原生业务日志。真实 A→A+B→B：原 TLS/Rust Game B READY先于A Stop，单侧唯一Rust TUN reader，两代FEC parity copied，健康lane在第一lane受损时不HOL；真实UDP前5后5、外层普通意图1460B、物理切后1280B、内层OS读回1178B，同安装/32不变。该真实 source 的8个TCP重组 ClientHello（旧4新4）均原TLS首载荷、ServerHello先出、无 WB-R1/私有前导；8个不同32B SessionID，2代各自独立本地源端口但同一server443。独立 Normal [Action41767053667](https://github.com/lly8666/wbd-next/actions/runs/41767053667) 的 SOURCE d7bd 真实双侧抓包也PASS，不能混源。证据 `docs/evidence/M0/PLAN028-H1092-SOURCE67BA-GAME4-X86-OVERLAP-TLS8-20261104.json`。

H1087 离线32B route-key、缺key本地拒绝、去WB-R1及证书验证已[限定收口](../evidence/M0/PLAN028-H1087-SOURCE7B38-ROUTE-KEY-SCOPED-CLOSEOUT-20261104.json)；不要重测已过的首飞。完整TLS1.3 CertificateVerify/Finished转录、同配置Go/uTLS基线仍 OPEN。x86 Game4 overlap成功不推断其余六模式、Windows实际物理NIC、Android或CPU/p99通过，H998在线原连接MTU收窄FAIL及老ARM4FEC Action FAIL原样保留。

下一完整Linux任务依用户规则在**真实ARM64客户端+ARM64服务端**跑相同Rust Game共享reader重叠和8首飞：本批只更新唯一原ARM64原生工作流的验收，不新建恢复算法、不改成熟产品Rust/Go热路径；一次SOURCE编译，一场景。Windows独立工作不计入Linux平台轮换。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1092 x86 source67ba native Game4 FEC6 A→A+B→B with 5+5 UDP, single Rust reader, MTU1178 and 8 genuine TLS first flights PASS; native ARM64 overlap qualification next."}
```
