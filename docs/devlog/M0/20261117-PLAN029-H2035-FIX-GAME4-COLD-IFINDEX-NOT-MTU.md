# PLAN029 H2035｜Game4 CN 真实首错：把物理 MTU1500 错传作 ifindex

- H2033 SOURCE `d546da726800241926f499188df75ee98b2da43c` [原生 Action43909402223](https://github.com/lly8666/wbd-next/actions/runs/43909402223) 总体 **FAIL**。实际4 TLS lane/Rust GameAdapter、原Wintun/OS Apply/MTU1313、精确Defender TCP64917、Tunnel UDP真实双端、内部两Rust worker Stop/WAL恢复与关闭Wintun均PASS。不能把这次说成还没启动/完全没联网；CN Direct DNS FakeIP业务仍未成功。
- 真实client.log首个边界：`PLAN029_H1703_UDP_IF_FIRST_ERROR stage=set_ip_unicast_if win32=10022 ifindex=1500`，同SOURCE OS读回物理网卡`ifindex=25 physical_mtu=1500`。源码`m0_native_v4_windows.go`把`physical:=selected.physicalMTU`误作为`runM0NativeV4WindowsGame`第四参，Game冷源再当`physicalIfIndex`交WinSock`IP_UNICAST_IF`，值1500无真实网卡触发WSAEINVAL10022，直接解释CN53无响应。
- 本轮只将Game调用参数改为`selected.ifindex`并重命名Game接收形参`physicalIfIndex`，原MTU/NAT/Defender/TLS/FEC/单Wintun及Stop不动。补纯静态回归防未来把MTU作NIC index；同时原单Go manifest两条`create.result_blob`同步新Git blob；H2034 GUI帮助结果保持不动。H2035真实Game4 CN DNS/Direct TCP/UDP/Tunnel TCP/UDP/双Stop **NOT_RUN until new original Action**，原失败不改写。
```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H2035 fix real Game4 CN Direct physical UDP socket WinSock10022 by using actual NIC ifindex25 instead of physical MTU1500, source-lock both Go overlay files and preserve first failed evidence."}
```
