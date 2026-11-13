# PLAN029 H1745｜原签名Go/Rust V3 首个真实CN DNS FakeIP Direct UDP与Tunnel同场

- 已验证基线 `17405b156f58e1f7b03ab781dafc2f6ad7e54a7e` [Action43414888803](https://github.com/lly8666/wbd-next/actions/runs/43414888803)：签名Windows原Go TLS/Rust私有V3 Normal/all、独立WSL2 Linux TUN真实双向TCP/UDP以及四阶段no-WFP owned Stop **PASS_SCOPED_REAL**。其Tunnel-only证据绝不能当D1/D2两个出口通过。
- 本次只派一个新真实场景（提交标签 `[plan029-v3-real-direct-udp]`），不是旧028重跑。原Linux TUN增加确切owned测试别名`203.0.113.77/32`，使原Windows/Linux kernel UDP/TCP选择真正**非CN Tunnel**，避免把默认RFC1918 `10.66.0.1`在BypassLanCn模式下误标为Tunnel。
- 独立Linux guest在真实物理网卡监听一个UDP53 `www.cn.example` 的CNAME/A，和一个业务UDP46111；Windows原应用从认证租约发真正UDP DNS包到`8.8.8.8`，Rust QNAME分类后以唯一 `dns.direct=WSL真实guestIPv4`物理绑定查询，只有`FakeJournal` fsync后才可回注198.18/16 FakeIP；Windows app向FakeIP发真UDP，Linux真实socket核对Windows有效物理源并发送回包，原Rust唯一Wintun返回原应用。全部按这一SOURCE和不同OS实际socket证据验，**PENDING**。
- 单独报告真实签名两出口、CN FakeIP、物理DNS、真实Stop；未测Defender owned TCP、真实Tunnel DNS fallback、D3–D5/P1–P2和padding，绝不复用H1713 test-only ABI结果冒充029产品。
- 脚本已纳入源锁Python语法预检、保留旧真实Runner准备和官方驱动签名验证。不启动PLAN030。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Add one actual signed original Go/Rust V3 Windows+WSL2 two-egress CN DNS journaled FakeIP Direct UDP and non-CN Tunnel UDP/TCP live scene; preserve H1743 proven Tunnel-only source"}
```
