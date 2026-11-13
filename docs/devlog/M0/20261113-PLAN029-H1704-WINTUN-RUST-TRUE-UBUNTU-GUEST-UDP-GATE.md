# PLAN029 H1704｜独立 Linux guest 的 Wintun→Rust Direct UDP→Wintun 真实通路试验

- 收 [H1703 Action43350031538](https://github.com/lly8666/wbd-next/actions/runs/43350031538) 真 Windows WinSock socket 绑定源码 c50de35，Windows ifindex14/物理源10.1.0.21，`IP_UNICAST_IF` SET/GET字节序读回14==14、同一Windows宿主socket UDP逆回成功，4/4测试PASS。保留 [H1702 FAIL Action43349211216](https://github.com/lly8666/wbd-next/actions/runs/43349211216)，历史SET网络序/GET主机序误判不改写；新实测只是本地socket门。
- 本批不再重复本机echo：引入只在 `m0_v4_probe` 编译的Rust C ABI `wbd_m0_win_plan029_owned_udp_trial_v1`。Go测试进程真正创建签名Wintun 0.14.1，生成唯一installation/generation，查原PnP和DAD、精确owned只一条presented FakeIP /32测试route、借出原 `N4OriginalKernelPacketLease.BorrowRustNativeRing`。一个真实Windows UDP应用 socket bind租约IP并**由Windows内核按owned /32 route**发送测试datagram；**Rust拥有唯一WintunRx reader**且立即释放Wintun receive borrowed loan，不给Go逐包泵；Rust `PhysicalUdpSocket` 源IPv4/ifindex绑定后发送给独立真Ubuntu WSL2内核 UDP 46098；Linux进程回实字节 `-reply`，Rust验证connected remote、构造含正确IP/UDP checksum且显示原FakeIP的包后先备payload再WintunTx Allocate/Send；最终Windows原应用 socket 必须收反向响应才记PASS。
- 单 [H1704 Action workflow](../../.github/workflows/m0-plan029-h1704-wintun-rust-guest-udp.yml) 使用官方Ubuntu24.04.5 pinned image/SHA、真实独立WSL2 eth0、动态Windows到guest的非Wintun underlay路由、pin原Go a7a82，Rust1.85.1源锁DLL与Go一次构建；只新增一个精确owned WSL HyperV UDP 46098入站规则并在finally CAS删除，不接旧WFP。失败也上传first Rust stage/Go cleanup，不用同VM双Action A/B无证据对比。
- **资格边界**：WSL2 guest是另一个Linux内核，网络走同一Windows宿主的虚拟vEthernet；真跨系统endpoint但**不是独立物理互联网机器**，这次也尚未实测！此门没有原始Go TLS、Normal/Game4正式Wintun/Rust owner接线、通用CN DNS和FakeIP生成/TTL/共享CDN反例以及GUI/padding，不授予Product Applied/Ready。H1694真实Windows TCP本地内核A/B/C与H1697真实无旧WFP四阶段OS均保留旧SOURCE结果。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6","windows-native-transport"],"reason":"Collect H1703 real Windows IP_UNICAST_IF local bind PASS and add one signed original Wintun owned Rust UDP independent Ubuntu guest reverse network scene, diagnostic-only; preserve exact earlier FAIL and no product Ready."}
```
