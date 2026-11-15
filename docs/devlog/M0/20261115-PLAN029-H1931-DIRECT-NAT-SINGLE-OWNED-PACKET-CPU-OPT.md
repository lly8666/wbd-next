# PLAN029 H1931｜单份Owned TCP NAT数据包：零额外再拷贝，合并CPU与小TCP原生场景

- H1930从签名H1922 Go EXE 原Rust DLL线程TID严格归属：10GiB原进程CPU约95.7%以上为原Rust TX/RX，原Go是冷层；高负载Direct CPU +12.281/+10.604s/GiB相对于同WinVM物理对照仍需缩小。H1927真正384小TCP p50多0.45–0.66ms但首回包p99达15ms，Tunnel96B UDP p99 10.655ms；不能盲删一条有进展续票。
- 原Rust `DirectTcpNat::to_listener/to_app` 借用输入`&[u8]`，`rewrite_tcp`先复制到每次栈上的`[u8;65535]`，随后`NativeTcpActor::enqueue`又分配`Vec`并复制一遍给有界256回复FIFO。每次Wintun Direct TCP数据/ACK段多一份不必要的拷贝和大栈数组（优化编译器可能消除部分清零，不能把清零次数当作已证CPU时间）。
- H1931严格保留借用输出接口供旧ABI/测试，抽出完全相同的`rewrite_tcp_fields`、共用`listener_entry`、`reverse_entry`对 NAT 端口/真实IP/旧checksum进行原有验证；新`to_listener_in_place`/`to_app_in_place`只修改**已经完整持有的同一个Vec**的IPv4/TCP地址端口、增量TCP checksum、IPv4 header checksum，成功后`enqueue_owned(Vec)`直接移交原FIFO。DNS TCP/普通Direct TCP/反向内核返回均走相同路径。拒绝无SYN、错误归属、满队列等 fail closed，不改变任何真实业务包字节、额外端口、LAN/CN/外网分流、转发线程、协议或Wintun owner。
- 两组新增Rust纯测试：普通、1B、64B、真实MTU、16KiB及65535B最大IPv4报文，老借用转换 vs 新原地转换 **完整字节相等**，含IP/TCP完整checksum；反向未命中不得修改packet/污染DNS fallback，no SYN不得分配端口；借用输出过小仍不分配 NAT identity。Retired和队列pressure保护不变。
- 原有一轮签名Normal P2的4MiB/384 small/10GiB marker以前相互排斥。H1931仅允许同时声明 `[plan029-v3-real-p2-bulk] [plan029-v3-real-p2-small-tcp-latency] [plan029-v3-real-p2-500-700] [plan029-v3-real-p2-long-ab]`时**先做4MiB真实物理/Direct SHA/FIN、再384条同机小TCP A-B-B-A、再同一原owner 10GiB物理-vs-Direct 500/700/CPU/GiB**，全程96B Tunnel UDP，Windows+Linux原产品 Stop一次。这减少独立Windows编译、相同source双Action以及额外真实测试轮次；旧单一场景标记逻辑保留，短H1898/128/sustain/旧ABBA仍互斥。
- H1931 未运行时不称CPU下降。新同机物理 vs Direct可以比较当前产品CPU额外开销，但H1922旧SOURCE运行于不同Windows VM，两次绝不能直接称旧新二进制因果A/B。必要时后续仅针对明确热路径做同机旧/新双二进制、上下限可解释的A/B，不再因单纯工具更新刷长压测。
- PLAN029 D1–D5/完整P1/P2、IPv6/Game4/GUI/padding仍开放，PLAN028限域保持、PLAN030不启。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1931 one-Vec in-place original Direct TCP NAT rewrite and single signed combined small-latency/long-10GiB verification, not yet native qualified."}
```
