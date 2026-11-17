# PLAN029B H2099｜普通CN双DNS同海外A、双端TCP/UDP及owned Stop真PASS

H2098 `SOURCE=d9435610939774e601895d9dd998ec828174ef0f` [Action44078530417](https://github.com/lly8666/wbd-next/actions/runs/44078530417) **SUCCESS**，真实签名Windows2025 Npcap/Wintun + 原Go TLS/Rust + WSL2 Linux Rust；原始artifact14327500131 SHA256 `13a6340f2da28d3e1113bc784711a515c62190e4755829a33633d7729d4b1c1e`；manifest source/product/fixture/Linux相等，原Windows EXE SHA256 `bc1f6ee5c446b7de91de386ea2f881e11541f2bec3fb6d8c65b8e3c29e86d236`，DLL `c4657a10d32be7a49ad6515aa71f3e3f1f68b9a681b332f777f76535279ac097`。原始report `mode_public=PASS_ACTUAL_WINDOWS_LINUX_NATIVE_normal`、`tcp_duplex=PASS_ACTUAL_TWO_OS_KERNEL_TCP`、`stop=PASS_BOTH_OWNED`，Npcap finally清理PASS。

独立原Windows AF_INET：有效`route_mode=2,business_split=true,cn_domain_fakeip=false`，CN `www.cn.example` 物理Direct DNS得到真实`203.0.113.77`、CNAME和TTL2；非CN `www.globalx.example` Tunnel DNS得到**同一个真实A**。Linux物理/TUN各观察**唯一有效一次**上游A请求；两个原应用UDP业务均在原Linux TUN接收与回显、物理业务0。宿主另有一条`www.msftconnecttest.com` 背景A在**正确Tunnel出口**，与本场固定transaction ID不同，夹具限量记录未计入有效请求。旧H2093反向TCP临时ACL问题在本轮原系统双向内核TCP都实走40B并回显，已通过精确test-owned允许规则及finally删除；并没有重写产品TCP/Defender。

这是 **B2普通CN一个独立Normal场景的PHYSICAL_PASS**，不是B2高级FakeIP、B3真实IPv6、B4跨代GUI/Game或B5同VM性能。原进程采样0.75 CPU秒、WS峰值44,982,272B仅供资源观察，不能除以不同VM交付GiB推CPU改进，也未采样小TCP/UDP p99。下一步按成熟H1808/D3夹具做单场高级CN映射；已发现Rust `stage_sources` 跳过IPv6不计已消费批次，B3将最小修复后以**真实IPv6报文/路由**验，不用无IPv6默认路由假装已拦截。

保留H2093/H2094/H2095真FAIL与H2097无触发NOT_RUN，029/030尚不收口。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Collect exact signed H2098 current SOURCE ordinary CN real-A dual DNS/shared CDN Tunnel UDP, bidirectional native TCP and owned Stop into original feature card; advanced/IPv6/performance remain unverified"}
```
