# H2171｜PLAN029非Windows Linux双原生ISA客户端/服务端高效测试

用户要求Linux服务端与客户端分别在x86_64、ARM64执行PLAN029相关测试，不重复已经签名的Windows20场Game分流或Game padding六场。本次限共用Linux成熟原Go TLS / Rust数据面；Windows专属WinGUI、Wintun/Npcap、WFP、FakeIP和CN直连/双DNS不能在Linux冒充资格。Linux own-TUN disable_ipv6与Linux原生路径MTU/真实业务属于相关非Win范围。Linux没有Windows startup-padding V5独立开关，不能把Win Game tls/flows当作Linux已实现。

一个全新[Linux原生双ISA workflow](../../.github/workflows/m0-plan029-linux-dual-isa-native.yml)（路径相对doc仅示意），两个平行作业：
- ubuntu-24.04上`uname -m = x86_64`，ELF62，真Linux双隔离netns、一套原始Go客户端/服务端；
- ubuntu-24.04-arm上`uname -m = aarch64`，ELF183，真Linux双隔离netns、各自原Go客户端/服务端，绝不以QEMU-user/交叉编译冒充原生。

每个架构只从同SOURCE组装一次原认证Go TLS客户端/服务端与Rust M1/M3/M4（ISA-L固定原commit）及一次Go/Rust定向单测，产出三二进制SHA256清单。顺序独立运行5个最小模式：Normal、Normal Fixed、Normal Auto、Game2、Game4/FEC fixed6。不跑旧长时间性能/弱网/五客户端矩阵；每个真实netns会话重建、TLS/原内核AF_PACKET及TUN建立、双向真实内核ICMP并用额外普通Python kernel socket验证双向UDP和TCP echo、Normal外层1460内层MTU+DF真实边界、仅各自TUN的disable_ipv6=1、FEC请求与实际应用计数/Game4 parity、双方真实owned Stop及namespace清理。首个真失败即终止该ISA后续场景并保留日志，另架构不受影响。

复用`tools/arm64_linux_netns_smoke.sh`的旧ARM64默认未动，通过显式`WBD_PLAN029_LINUX_DUAL_ISA=1`允许两ISA/切换束路径及当前原生socket探针；原本受支持的冻结ARM64、netem和容量试验不改变。只允许commit`[plan029-linux-dual-native]`触发昂贵原生工作；workflows的普通路径push单跑空作用、无需每个修改重测。全案SOURCE签名保留历史: H2169 Windows网络PASS是另SOURCE81998，当前Linux实网**NOT_RUN**直到新的Action job真实结论产生。

本批只有工作流和夹具（无产品Go/Rust网络逻辑、没有GUI改动），本轮初始只更新游标/devlog；原生结果后补功能卡/证据。完整029/029B技术出口仍OPEN，030未启动。

```feature-impact
{"kind":"none","ids":[],"reason":"Add source-locked native Linux x86_64/aarch64 client+server test harness and workflow only; do not change product features or promote non-run native network evidence."}
```
