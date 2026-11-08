# PLAN028 H1382：Windows 两个真实签名原始产品同时认证试验

2026-11-08。H1381 实际 Windows2025 双账号内核占用门禁成功后，原完整 Windows2025↔Ubuntu WSL2 workflow 尝试同时启用两条真实 Go TLS443/Rust M4/Npcap/签名 Wintun 产品会话。

两个独立受保护账号 Alice/Bob，各自原 Go CLI TCP源端口41031/41032、安装及 tunnel identity、Wintun alias/WAL、Windows OS /32 10.66.0.2/32和10.66.0.3/32；共享原 Go server TLS443按真实认证选手动租约，并用一个服务器 Rust M4 kernel TUN。Windows 两客户端必须都实际 Ready、两张 OS Wintun index/GUID 不同，真 Win32 UDP 回声和 TCP echo 后 A exact Rust/WAL Stop，B 仍 UDP 增长并 TCP echo，最后 B exact Stop、服务器共享 Rust TUN Stop。所有未达门项按原始真实证据独立记录，不把先前 Linux 双账号 PASS 或 Windows 双 Wintun OS driver PASS 拼作本试验成功。

仅在 commit 含 [plan028-win-dual-original] 标记时原完整 source-locked workflow 选择双产品原生 fixture，其余 Normal/游戏模式不变；原日常 Windows 单实例保护不变。H998 hot PMTU 原失败和 L3 两条1800秒均仍独立开放。

```feature-impact
{"kind":"none","ids":[],"reason":"H1382 test-only two original authenticated Windows Wintun native products scenario in exact-source complete WSL2 workflow; no Go/Rust product wire change and no feature verdict is promoted before actual test."}
```
