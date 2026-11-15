# PLAN029 H1941｜原生短TCP首回包FIN合并窗口优化和P1 CN合成规则修正

## 已签收前态
[H1940 original Action43738050095](https://github.com/lly8666/wbd-next/actions/runs/43738050095) SOURCE `601d540401b7d516bf1e1dfaa9c2998cce07defb` **SUCCESS** 原Windows Go EXE/Rust DLL/Wintun/Npcap/WSL2 Linux TLS+内核业务：4MiB原生TCP、384条64B/1KiB/16KiB小TCP物理/Direct A-B-B-A全量SHA/FIN、并行96B Tunnel UDP120/120、Owned Stop均PASS。但 Direct 首echo-after-half-close p99 **15.360/15.764/15.567ms**，物理 **0.321/0.425/0.905ms**；ready票据最大等待**23ms**且FIFO峰值1；Tunnel UDP p99 9.352ms。H1938首次read ticket与H1940 WAIT_ANY三组优先级轮换都没有消除尾延迟，未关闭P2。

## 本次Rust数据面候选
服务器必须读完整请求及`recv(0)`才echo。原Rust WinSock Relay读正字节后若`FD_CLOSE`被合并到该event，通常在下一TX轮才读0并向另一条内核TCP`shutdown(SHUT_WR)`；刚好可能遇到8~23ms的服务票据等待。H1941只在**真实FD_CLOSE且相同方向本轮read>0**后追加**一次非阻塞 TcpStream::peek([u8;1])**，它不消费payload：返回0才标记原收件EOF，现有待写队列为空时同轮原规则向对端转发FIN；返回字节/WouldBlock/Interrupted保留原状态和H1920正读或写进展自续票；错误原样关闭本流，非周期轮询、不新增独立线程、Go热泵/第二Wintun或扩大资源。H1916 coalesced FIN+32KiB回归严格保留（允许同轮确定性EOF或原有后续探测），另加Windows两个真实loopback kernel socket 64B data+FIN单轮正反向回归，确保字节/FIN和Stop语义。P2自诊断聚合`inner/outer_fin_peek_calls/eof`及计数合法性，普通DATA不会触发新peek syscall。

## 独立P1 ABBA
H1937同Rust V3 A1(all)真正双向约50Mbps且CPU21.6792秒/GiB，B1(CN)真正同源业务/Stop通过但`cn_rows=8`不合4096规则门；旧测试合成`100.64.0.0/10`属于CGNAT LAN，原Go splitroute缩合/覆盖。H1941**仅测试fixture**将4096间隔/32换到不命中LAN或Linux TUN203.0.113.77的`11.42.0.0/19`，保留原CN >=4096、domain_bytes>=100000严格门。P1四臂原生尚NOT_RUN，本次只启动一个P2短场，不重跑10GiB；测试专用公有IP并非产品国家IP数据。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Source-locked FIN-closure one-shot non-consuming peek in original Direct TCP plus P1 non-LAN synthetic CIDR fixture, native proof pending."}
```
