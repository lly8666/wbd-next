# PLAN028 H1079｜Windows 原 Npcap↔WSL2 标准 TLS 首载荷真实 PCAP 验证入口

H1078 已通过 ARM64+ARM64 Game4固定6两代共8条原TLS真正TCP首飞，**不等于 Windows Npcap 实际出口的首载荷已经抓包验证**。旧Windows↔WSL2跨OS试验 `tools/m0_wl_public_normal_e2e.py` 仍把用户已否决的已知常量 `route-key` 写进源码，并在Linux WSL2生成自签证书后没有给Windows新原TLS客户端导入应用专属根。这条夹具即使业务/Stop之前PASS，也不能按新 `TLS_HANDSHAKE_CONTRACT` 的首轮证书验证/密钥配置合格；不是要改Rust或另造恢复器。

本次按单个完整Normal Windows+WSL2工作包修正：
- 使用Python CSPRNG离线生成32B route-key一次，Windows客户端通过 `--route-key-hex-file` 本地导入，Linux WSL2 server得到同源0600常规私有文件。不把值塞进argv、日志或产出工件，出场后两端删除，不做网上挑战、WB-R1或任何TLS前交换。
- 将本场景生成的server证书 via Windows `--tls-ca-pem` **应用级证书信任**传入真正原Go TLS，保留目标SNI及账户密码验证。默认用户外层IPv4 MTU 1460（省略显式MTU配置），不是1500。
- 在真正 Windows Npcap client 发SYN之前，从真实WSL2 `eth0`启动有界tcpdump，待原TLS/Rust READY后 Stop该准确捕获进程；复用同一 `m0_plan028_tls_wire_audit.py` 并仅参数化动态实际WSL2 server IPv4，逐TCP序列重组双向TLS记录并断言客户端首载荷ClientHello、服务端无提前数据、合法32B兼容SessionID、TLS13扩展、无WB-R1。可变record长度仅报告，不按包数或固定长度硬编码资格。原PCAP留runner并即时删除，CI只可上传脱敏审计摘要。
- 既有main Windows-Linux工作流仅在本提交 `[plan028-win-tls-wire]` 选一个Normal实景，构建一次当前SOURCE的双OS原Go/Rust产品，不触发七模式/老吞吐矩阵；Windows ABI、Game、FEC、Stop均不改。Linux下次独立双端工作包仍是x86/x86；此工作包是Windows+WSL2，不计入纯Linux同架构轮换。

**新Windows real Npcap Action之前为 IMPLEMENTED_NOT_TESTED**。Windows真正的物理NIC/source-IPv4切换、完整TLS Finished/外部基线指纹、健康Game重叠/CPU/p99不从本场景获得资格。H998在线热缩MTU FAIL、旧ARM64 Game4FEC Action FAIL、Android未测及远端ICMP未测继续保留。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1079 Windows original Go Npcap↔WSL2 real TCP TLS first-flight candidate, offline 32B route key + trusted self-signed CA + bounded actual server eth0 capture, no raw PCAP artifact; native Action pending."}
```
