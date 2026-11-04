# PLAN028 H1086：Windows Npcap ↔ WSL2 真实 TLS 首飞限定 PASS

[Action 41761356866](https://github.com/lly8666/wbd-next/actions/runs/41761356866) SUCCESS。独立下载 artifact 13290631778 的27个文件，核验源锁 Windows EXE/Rust DLL manifest、WSL2原Go/Rust二进制来源SOURCE `7b38d2baddaa41ab5e410d2533a1e8c396510745`（H1080构建工件复用、没有重复编译）、真实原生 `mode-results/normal/report.json` SHA256 `dbef0055...`、direct-full.log SHA256 `1a09ab...`。

Windows Npcap 客户端↔WSL2真实 Linux eth0 tcpdump，从 SYN 之前抓并重组精确TCP四元组，首个客户端有效payload为TLS ClientHello **667B** record，服务端首个为ServerHello **127B**，客户端兼容SessionID为32B、15个TLS扩展，**没有WB-R1前导或ClientHello前服务端应用载荷**。这两个长度是**实测**，不是固定包数/包长规则。32B route-key由本地CSPRNG生成、两端各自私有文件导入；客户端只信任本任务应用专属自签测试证书，TLS内真实账号密码验后才放业务。真实双向 UDP、TCP 以及双方原Rust Stop PASS。raw PCAP测试内销毁，上传工件仅为脱敏元数据和日志。

本结果为**TLS首flight外观+原生业务/Stop scoped PASS**；尚未对完整 TLS Certificate、CertificateVerify、Finished transcript做独立的会话层对照，也未做相同 SNI/证书/MTU 的标准 Go/uTLS 参考基线比较，不声称外部站点指纹或任意 DPI 不可检测。Windows真实物理NIC/sourceIP切换和健康Game重叠还未验。H998在线MTU缩窄FAIL、旧ARM64 Game4FEC历史FAIL、远端ICMP及CPU/p99因果未证按原范围保留。Windows+WSL2不计入完整Linux x86/x86→ARM/ARM平台轮换任务。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1086 original Go/Rust real Windows Npcap to WSL2 TCP ClientHello/ServerHello and protected UDP/TCP Stop PASS, full Finished/baseline and Windows physical NIC not qualified."}
```
