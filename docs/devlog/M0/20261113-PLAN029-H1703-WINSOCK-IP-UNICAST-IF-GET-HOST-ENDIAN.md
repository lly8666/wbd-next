# PLAN029 H1703｜WinSock IP_UNICAST_IF 读回端序修复；保留真实失败

- 收回 [H1702 source 7ac13ab Action43349211216](https://github.com/lly8666/wbd-next/actions/runs/43349211216) **FAIL**：真实Windows2025选物理 NIC ifindex14/source10.1.0.8，3项纯UDP/IP checksum测试 PASS，真实socket在 open 的 `InterfaceBind` 处退出，未到应用send、对端echo、Wintun。原始artifact [14003041952](https://github.com/lly8666/wbd-next/actions/runs/43349211216/artifacts/14003041952) ZIP sha256 04f8c204ba32687a2c1ae787436518c737484a7b66dfebc3bffa0f8970f21fdd。不可把单socket诊断看成029双出口或性能结果。
- 明确首个源码差异：Windows 官方 [IPPROTO_IP/IP_UNICAST_IF契约](https://learn.microsoft.com/en-us/windows/win32/winsock/ipproto-ip-socket-options) 规定 setsockopt 的 IPv4 ifindex **网络字节序**，getsockopt 返回 ifindex **主机字节序**。H1702 在GET后又调用 `u32::from_be(observed)`，会将Windows x64正常host值误判不等。H1703在保留SET `ifindex.to_be()` 的同时直接比较 GET `observed==ifindex`，没有降低/取消精确物理接口绑定，避免走回Wintun/默认路径。
- 修理合并错误观测：分别记录真实WinSock `setsockopt`、`getsockopt`、读回比较、`UdpSocket::connect` 四个cold阶段。前两处通过 WSAGetLastError，读回记录requested/observed/byteswap/len，连接记录OS error。所有规则只有冷路径ERROR日志，无每包日志或OS查询；socket出错Drop关闭，绝不fallback到无绑定socket或Tunnel；不关Defender、不改WFP/第三方配置。
- 复用唯一 [H1702 workflow](../../.github/workflows/m0-plan029-h1702-physical-udp-bound-socket.yml) 由新source变更自动跑一次同性质实际NIC本地listener往返；若 PASS 仅证明物理source+ifindex绑定和**同宿主**UDP往返，不表示出物理网卡，更不表示Wintun→物理Direct→Wintun。H1694 TCP内核A/B/C及H1697 no-WFP Win32四阶段依旧是已通过但不同的场景。Rust NativeOwner、DNS53、FakeIP TTL、GUI/startup-padding、D1-D5/P1-P2仍 OPEN。

```feature-impact
{"kind":"updated","ids":["windows-native-transport","dns-split-ipv6"],"reason":"Record actual H1702 physical WinSock FAIL and fix IP_UNICAST_IF GET host-order readback with exact cold boundary errors; retain all earlier source-scoped evidence."}
```
