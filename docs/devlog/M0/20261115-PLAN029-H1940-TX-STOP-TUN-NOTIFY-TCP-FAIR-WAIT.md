# PLAN029 H1940｜真实384小TCP再次确认首回包15ms，修Rust TX等待事件优先级

## 完整源锁收据
[H1938 Action43735936831](https://github.com/lly8666/wbd-next/actions/runs/43735936831) **SUCCESS** exact SOURCE `3e80fc8c7b7d723a618a91b7c47a351c99d3dfef`：原Windows Go EXE+Rust DLL、签名Npcap/Wintun、WSL2 Linux真socket/TLS+双端Stop；4MiB物理37.628ms/Direct147.313ms全部SHA/FIN，384条64/1024/16384B真实kernel TCP物理-Direct-Direct-物理各64条，每条Linux真实收件、总SHA `0425643d53f93dc3d3e43049f4934b321b18c14d655400e07a93767db4b17f8a`、FIN全PASS；96B Tunnel UDP120/120，p99 9.005ms，双端owned Stop PASS。

**尾延迟仍未解决**：64B首回包p99物理0.825ms/Direct15.025ms（Direct p95 13.765ms）；1024B物理0.708ms/Direct13.461ms；16384B物理0.979ms/Direct7.185ms。Direct完整请求p50比物理多约0.79/0.76/1.18ms。新增H1938连接后首次读票据**194**次实际触发，维持完整业务；Rust ready FIFO峰值1，但服务票据2127次中≥8ms72次、≥16ms4次、max24ms，说明不等同于高队列深度，可能是TX事件唤醒/OS调度公平性。H1931不同Runner比较仅描述，不是因果A/B。

## H1940低成本且可回退的实验
Windows官方[WaitForMultipleObjects](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitformultipleobjects)在WAIT_ANY多个句柄同信号时**固定返回索引最小的句柄**。原Rust TX等待数组始终`[Stop,Wintun,RX-Notify,16个WinSock shards]`，繁忙Wintun更易抢到等待结果，可能使Direct TCP socket就绪通知迟到。H1940在**原同一个wait调用**按3阶段轮换`Stop/Tun/Notify/TCP`、`Stop/Notify/TCP/Tun`、`Stop/TCP/Tun/Notify`：Stop永远0且抢先、三业务类别各获首选机会，全16个原shard句柄一一映射原port，不新增poll、定时器、线程、锁或系统调用，纯all Tunnel保持原3句柄顺序。WinSock receive/IO/liveness规则不动，H1920任一读写正进展续票不动。新增Rust纯结构回归＋Python廉价真源码排线检查，避免静态断言只看存在标记。

H1940 **源锁真实 Windows/WSL2短场尚未跑**：复用H1938真实4MiB+384小TCP+UDP/Stop，报告每大小首echo p50/p95/p99/完整请求、Rust ready≥8/16/max和WinSock事件计数；若没有减少尾部或出现业务失败则不承诺收益。H1937 P1 ABBA合成CN4096曾错误落在LAN 100.64/10而被原Go Normalize吞为8条；独立已备不重叠11.42/19修正版，不能与本次短场并行发昂贵Action。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Signed H1938 Direct TCP first-echo still high; test-only design of bounded single-wait Rust TX Tunnel/notify/TCP priority fairness while preserving owner Stop and liveness."}
```
