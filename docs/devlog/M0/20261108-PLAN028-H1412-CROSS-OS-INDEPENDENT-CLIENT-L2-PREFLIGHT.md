# PLAN028 H1412｜Windows 一 VPN + 独立 Linux netns 客户端同服的 L2 可行性最小实验

2026-11-08。用户明确更关心 Windows 单机单实例与单服务器多独立客户端，不再为同机第二 Wintun 写产品例外。既有 H1407 Windows signed Npcap/Wintun 对端是 WSL2 Linux **服务端**，H1372/H1392 Linux 多客户端在 Linux netns 中。尚无**同时连接**的 Windows 原客户端+Linux 原客户端同服业务回执，仍 NOT_RUN。

当前原 Windows CI Runner 一块 vEthernet 连接 WSL2 Ubuntu eth0；同 guest 的第二 Linux 原客户端需要物理 veth netns 转发到原 server 与 Windows 可见的共同 NIC。直接各写一次仿真 READY、localhost socket不具有真实 TLS/FakeTCP/NPF/TUN 资格。先做一条严格 underlay-only 原生预检：临时 bridge MAC 保持 WSL2 eth0 原 MAC、真实 eth0 IPv4/default route 临时接至桥，Linux 独立 netns veth 加入桥；Windows 宿主 UDP socket→原 WSL2 eth0 IP 与 Linux netns veth UDP socket→桥别名，全部实际 kernel echo 和 L3 回程；最后精确恢复原 eth0 IP/default route、删除自有桥/veth/netns 与临时 HyperV UDP 单端口规则。实验 **不运行任何 VPN 客户端/服务端，不能算 PLAN028 L1 PASS**。若宿主 WSL2 bridge unsupported 或 Windows inbound 失败，标为 `ENVIRONMENT_BLOCKED_UNDERLAY_PREFLIGHT` 并保留日志，不把 OS 虚拟交换机缺口推给产品。

实验成功才把成熟 H1382 一服务器多账号与 H1407 Windows 原生单客户端接线组合为一条真实 Win VPN + Linux netns VPN 同时业务/Stop；未经完全认证和业务不得宣称同服隔离。Windows/Android物理实际机仍 NOT_RUN。H1411 已用三平台七档 ISA-L真实编解码+Win原认证 owner 元数据留痕，PLAN028 IN_PROGRESS。

```feature-impact
{"kind":"none","ids":[],"reason":"One native CI-only L2 bridge underlay feasibility check with strict cleanup before attempting missing Windows+separate Linux client actual product scenario; no protocol, hot loop or product code change."}
```
