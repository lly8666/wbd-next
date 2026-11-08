# PLAN028 H1364｜Windows 签名原生同源 IPv4 物理 MTU 收窄｜原始 PASS

2026-11-08 的原始 [Action 42448657827](https://github.com/lly8666/wbd-next/actions/runs/42448657827)，产品/原包 SOURCE `04dbda77d0bcb85ea4e01b3c3a7ba9aae42f073a`，**全六个原始任务 SUCCESS**，其中 Windows 实机原生业务、独立 Rust/Go 编译、WSL2 真内核、签名 Npcap/Wintun 安装、最终 cleanup 均完成。最初「仅派发」记录现以原结果取代，产品按真实原生证据 **PASS_SCOPED**。

本场一个真实 Windows/WSL2 原始 Go TLS443 + Rust Normal Off（非七模式矩阵），同一个受控 WSL vEthernet ifindex **25**、同一个 Windows source `198.19.254.1`，OS `NlMtu` **1500→1280**，同步通过 Windows 真实接口读回。Windows SYN MSS **1420→1240**，两代真实 Wintun 内层 OS MTU **1389→1209**；独立 Linux server 的 SYNACK MSS 保持1420、Linux TUN MTU1389，不能误称 Linux 同降。Windows 原生 TLS 两代源端口41031→41032，两个原始服务端 Rust 认证会话，旧代 Stop 后新 TLS/Rust Ready，用时 **11,656ms**（从系统变更至新就绪，不是稳定业务无收件间隔）。

原系统 UDP：Windows发送92/收94、Linux发送223/收90，双方真实内核 socket；新代真实 UDP 接收增量 Windows11、Linux4。真实 TCP 双向双方各收37，回声均通过；`app_duplex=PASS_ACTUAL_TWO_OS_KERNEL_UDP`，`tcp_duplex=PASS_ACTUAL_TWO_OS_KERNEL_TCP`，`stop=PASS_BOTH_OWNED`。服务端共享 TUN Stop 已join、0排队满丢；Windows Npcap ingress 本地 drops0。原始 mode batch `normal=PASS`，原始 `direct-full.log` 为 `WL_PUBLIC_REAL_MODE_RESULT normal PASS`，作业 `native-public-two-os` SUCCESS。

原始受控脚本在 run-scoped Stop 后恢复 `NlMtu=1500`，测试自有 Windows/WSL 别名清理且默认路由未变化；Windows Npcap 原生服务也清除。原始 ZIP artifact **13604034725**，28 文件，字节24476，SHA256 `aa4234e83dcfa1e9d80fcf376157f281412675aa6f30e9598f6fb7ca272de64e`，CRC 28/28 PASS，包含原始 OS receipt、两代 TLS/MSS、UDP/TCP应用回执、客户机/服务端日志。详细 [H1364 原物证索引](../evidence/M0/PLAN028-H1364-SOURCE04DB-WINDOWS-NATIVE-SAME-IP-MTU1280-REAUTH-UDP-TCP-STOP-PASS-20261108.json)。

**索引修整**：只缩短功能卡冗长历史描述，并把 cursor 限制为原八条上下文引用，保留所有真实 source/evidence 及原失败；不重跑网络、不改动 H1364 原生 PASS。

**边界**：这是短时源锁的真实物理 MTU 变化后**冷代重新认证**资格，不豁免 H998 同 socket 热 MTU 原失败；并非两个独立 Windows 客户端同时认证/隔离，也非持续压力、Android/物理 WAN 或 L3 两条1800s。H1362 原 native CI reporter KeyError 虽是外因假红，其真实 APP/Stop 仍按 H1363 原物证离线核验记 scoped PASS，历史 raw CI FAIL 另留。PLAN028 仍 IN_PROGRESS。

```feature-impact
{"kind":"updated","ids":["path-mtu-budget","windows-native-transport"],"reason":"H1364 source04db original signed Windows Npcap/Wintun real WSL2 native Normal same source4 interface25 OS MTU1500-to-1280 with two authenticated Go TLS/Rust generations, native UDP/TCP and exact owned Stop plus full OS cleanup. Original Action SUCCESS, original 28-file CRC-verified artifact indexed without mixing x86/ARM sources."}
```
