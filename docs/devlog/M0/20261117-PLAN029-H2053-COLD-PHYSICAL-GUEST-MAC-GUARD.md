# PLAN029 H2053｜原物理 Cold DNS 的 WSL guest OS MAC 精确约束

- H2047真实物理dns.direct UDP53超时，已在H2050补充仅原Windows/WSL2测试源的UDP/TCP53 HyperV规则。同时代码核实：`m0_native_v4_windows.go` 原始FakeTCP在实际 WSL2 网络已证实SendARP会把 guest-IP 解析成 **Windows vEthernet host-self MAC**；普通FakeTCP从已OS核验Linux eth0 MAC纠正，**之前新增的物理DNS bootstrap没有复用这段修正**，因而尚不能断言只有防火墙原因。
- 现只在四元`WBD_PLAN024_NATIVE_VERIFIED_{GUEST_MAC,GUEST_IP4,HOST_IP4,IFINDEX}`完整存在并与实际`DiscoverPhysicalUnderlay(dns.direct)`的IP、ifindex、真实源MAC和下一跳（guest或真实host-self）一致、第三方gateway严格拒绝的情况下，把cold NPF UDP以真实Linux guest MAC送到同一个 resolver。无环境时不改变普通生产自动发现；不允许未知地址、网卡和DNS回退。新增原Windows Go纯测试覆盖匹配、无evidence不修改、错误接口/地址、第三方网关和部分证据拒绝。
- ABI原生overlay manifest两处blob在同提交按Git对象精确sha锁定，仍不得仅凭Go编译声称原DNS UDP TC/TCP53实网PASS。当前H2051真实原生Action正在跑，另H2050 GUI真按钮独立Action在途。用户排除IPv6/P1/P2和重复H2031/H2041继续尊重。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Original cold physical DNS WSL2 selected guest L2 path attestation to avoid host-self MAC, no alternative resolver; precise source manifest locks and Windows Go unit, pending native."}
```
