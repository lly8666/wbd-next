# PLAN029 H1933｜物理CPU指标纠偏和Rust分流规则ABBA判分器

**不同问题用不同基准，不可混用。** H1931原签名10GiB物理TCP原Go+Rust进程CPU约0.320/0.307秒/GiB，因为Python业务socket直接走Windows→WSL2物理网络，根本不进入Go/Rust客户端；Windows kernel、Python、Hyper-V、WSL Linux、驱动ISR/DPC不属于所测原进程。Direct比这个物理阶段额外11.758/9.839秒/GiB可衡量Native Rust TCP双内核腿+Wintun/NAT/回注的整体增量，但**不是分流规则分类CPU**。

历史H1863 `tools/m0_plan029_h1814_p1_tunnel_ab.py` A=旧V4 Tunnel/B=新V3 all Tunnel，50Mbps两腿60s，CPU差约7.01%，有实现/冷配置差，不能把它叫classifier新增开销。需要新四臂本地同Rust分流策略试验：
A1 Rust V3 route-mode all → B1 Rust V3 bypass-lan-cn → B2 Rust V3 bypass-lan-cn → A2 Rust V3 all；同一SHA Go EXE+Rust DLL/Linux真正Rust二进制、Win2025 Runner、原始Wintun/Npcap、同Linux TUN、TLS原owner、MTU/修复/FEC/pace不变，独立每臂Windows+Linux owner Stop/WAL还原、每臂60s/双向各50Mbps/25ms真实kernel qdisc/0%注入loss。**必须使测试双方的所有真实应用流量访问Linux真实owned TUN公有别名203.0.113.77/32**，它既不是10.66/24 LAN，也不在4096 CN模拟前缀或198.18 FakeIP范围；否则B会把流量改走Direct，不能用来测Tunnel额外分类。B载入4096个不连续CN /32（100.64.0.0/10稀疏合成规则）+8192个DNS域名规则；Go只冷编译，不上线每包Go callback。B的OS多持有必要CN冷资源，是**启用真实分流模式的总增量**，不宣称纯指令classifier耗时。

新 `tools/m0_plan029_h1933_abba_math.py` 仅接收四臂已经由真实源锁验过的report：必须同源/同二进制、original Rust trial ON四次、各自成功Stop、每个应用真实/Tunnel public alias、双端业务goodput≥47.5Mbps/RTT≥200次、每臂Rust TX/RX线程原Win32 TID采样>=45个。CPU按 **Windows original Go+Rust进程实际CPU秒 / Windows+Linux实际首收业务GiB**，B均值−A括号均值，另列A1/A2漂移、B1/B2重复、交付量差(>3%时明确 INCONCLUSIVE)、每臂UDP p99。四段足够消除一阶线性VM时间漂移，却不能凭两组判统计显著、不能减p99冒充逐包延迟。8项纯负测/正测加入已有廉价治理CI，**本H1933没有原生P1结果或CPU改善声称**。

独立另做P2：同机**全经过Rust Direct的数据路径**进行旧/新NAT实现A-B-B-A，或同机两种原产品二进制反平衡，测每GiB CPU、p99/FIN、Tunnel小UDP/Stop；不可用物理裸TCP替换旧NAT作为B。系统层CPU需独立WPR/WPA+ETW检查Rust线程栈、socket系统调用、Wintun/Npcap、DPC/ISR和Windows/WSL VM，现有GetProcessTimes只覆盖客户端进程。

参考Microsoft官方[WSAEventSelect](https://learn.microsoft.com/en-us/windows/win32/api/winsock2/nf-winsock2-wsaeventselect)、[WSAEnumNetworkEvents](https://learn.microsoft.com/en-us/windows/win32/api/winsock2/nf-winsock2-wsaenumnetworkevents)的原子收件/事件重置契约；不要为了降低零进展轮次破坏H1920证明的读写正进展公平票据。Wintun官方[单owner ring + event](https://git.zx2c4.com/wintun/about/) 可借鉴有界批处理与尽快归还ring，不宜导入第二Wintun或Go热泵。必要时参照[Microsoft WPR](https://learn.microsoft.com/en-us/windows-hardware/test/wpt/windows-performance-recorder)短采样，脱敏严控数据范围。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Correct physical CPU baseline semantics and add test-only fail-closed source-locked same Rust-V3 policy ABBA scoring; no native product change."}
```
