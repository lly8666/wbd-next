# H2285 · 把Windows原Npcap的WSL2物理侧网络路由到远端ARM真实TCP（先核内核路径）

## H2284 已验边界与下一真实障碍
H2284 [Action44932436553](https://github.com/lly8666/wbd-next/actions/runs/44932436553) 7/7完整双组三Runner Win2025 Winsock→独立ARM Linux relay→另一ARM Linux server，8×25s真TCP下 A clean direct1286/relay680/400ms493Mbps，B 1068/995/600Mbps。A在relay没有过800Mbps资格，B通过；中继 tailscaled 消耗1.53–1.88核，最忙单核48–58%，不能因当前OS裸TCP漂亮就晋级原WBD。H2228旧Linux x86/ARM/x86 + 双VXLAN无NAT原始Go/Rust模式曾800+ Mbps，但已证实与Win/ARM原生Winsock及Npcap不是同一个条件。

原产品的真实Windows Go+Rust/Npcap在 `tools/m0_wl_public_normal_e2e.py` 发送**二层帧**到同一Windows真实宿主的Ubuntu WSL2 `eth0`（原端点在guest `--raw-interface eth0`，原TLS443），并不等于Winsock到Linux Tailscale `100.64/10` 的原生内核TCP。原ARM服务器Go/Rust又需实际Ethernet AF_PACKET介质。**未经验证不可直接把Windows原--server-ip指向远端Tailscale虚拟L3 IP然后宣称真正Windows客户端通过。**

## 第一个有辨别力的内核路由前置（严格非WBD业务PASS）
新 `tools/m0_h2285_windows_wsl_route.py` 和 `qa-h2285-dual-wsl2-arm-route.yml` 仍使用已经实证成功的两套各三台不同GitHub VM，不额外申请第四台Runner：
- Windows2025原生**Winsock**端内部启动Ubuntu WSL2（同一Windows宿主的Linux guest，不算第四Runner），版本/下载哈希沿用已有H1706签名原测试，准备独立私有 `eth0`。仅在Windows当前宿主与guest自检源地址后加`iptables`精确来源/目的 TCP18727的 **DNAT/SNAT+FORWARD**，把真实Windows vEthernet来源的数据路由进同组ARM relay的Tailscale实际IP。原Win Socket看起来连向同Windows WSL2 guest eth0，guest上**没有任何TCP业务监听/代理/Go TLS server**；回包必须经WSL2原Linux conntrack reverse NAT返回Windows，模拟原Npcap外层先进入WSL2再出网的L3条件。
- 同组真正ARM64 Linux中继继续使用H2284已打通的Tailscale kernel DNAT/SNAT，不终止业务TCP。ARM server在另外一个独立ARM64 VM的实际内核TCP18727监听。两套独立source/run/group身份和真正client→WSL2→kernelRelay→ARM-server 4bulk25s/160echo（2MiB测试socket）都验证ARM真实字节结算；Windows端没有安装/启动Npcap或原WBD，所以 **仍不是原产品路径**。
- 服务端及中继分别读到实际OS socket与netem两向发包。WSL2必须证明真实 `nat PREROUTING/POSTROUTING` 计数正增长；中继两向真实qdisc packets也必须正增长；若任一方向缺失、tailnet走DERP、160回显未满或source/组错配，明确作为路由夹具FAIL，不报告WBD吞吐。Windows guest精确 `-D` 删除所加四条iptables规则，恢复guest原来`net.ipv4.ip_forward`，ARM真正sysctl独立finally恢复；工作流实际两个Windows和两个ARM server都上传失败证据，绝不把业务缺失当 PASS。
- 这只是原Windows物理侧 **L3路由前置**，不是原Npcap注入、Wintun TCP内层、ARM原TLS认证及AF_PACKET `wan0`，不会偷偷在Windows/WSL2端回显数据。前置成功只能确认两组三Runner的 Windows vEthernet→guest conntrack→tailscale→ARM relay→ARM kernel TCP 双方向真实可达。随后下一增量必须在WindowsRunner使用原签名Npcap/Wintun Go/Rust client（原H1706/H2273 assembly），ARM服务器使用原H2228构件并将其原raw wan映射到test-owned veth/netns，在原Tailscale/L3和真正以太AF_PACKET之间明确路由，只有TCP443原TLS/认证/owned Stop以及真TUN业务都成立才作产品优化。
- 优先复用H2284已证实千兆CI Tailnet端口 TCP18727，不请求新未放行的TCP443；原GoTLS产品TCP443将仅在受控test-owned Linux forwarder内部转换，不能放大Tailnet ACL或全部端口放行。若Windows WSL2 guest走Windows Tailnet失败，保留原失效路径而研究旧H2228 VXLAN二层受控数据通路；禁止不断在错误网络上扩大Rust队列。
- 本轮源码变化只有Python测量工具、受控WSL2路由与Actions workflow、源锁静态断言，**GoTLS/Rust、Npcap/Wintun驱动、原应用配置默认、所有原WBD Stop均不修改**。两个组执行完全相同4TCP25s＋160echo业务，fail-closed不选最好组。仅工作流commit含精确 `[m0-029-h2285-wsl2-arm-route]` 才调度六Runner，其余只静态。

```feature-impact
{"kind":"none","reason":"H2285 adds source-locked genuine Windows WSL2 guest kernel DNAT to independent ARM Linux relay to another native ARM kernel TCP server, two isolated 3-runner groups. Explicitly NOT WBD original signed Npcap/Wintun GoTLS/Rust product. All test-owned Linux iptables and sysctl restored, no production source/default/Stop changes."}
```
