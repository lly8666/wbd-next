# PLAN029 H2037｜Game4 同时消费真实物理MTU与物理ifindex，修H2035编译首错

- H2035 SOURCE `f8c8a019a01ade66b92dbee306beb02ad9f88e15` [Go编译Action43912881765](https://github.com/lly8666/wbd-next/actions/runs/43912881765) / [WAL编译Action43912881602](https://github.com/lly8666/wbd-next/actions/runs/43912881602) **FAIL**于 `cmd/wbd-client/m0_native_v4_game_windows.go:166:19: undefined: physical`，发生于链接原Go产品之前，真实Game4 CN新SOURCE联网 **NOT_RUN**。不同源 H2033 [Action43909402223](https://github.com/lly8666/wbd-next/actions/runs/43909402223) 才是真正跑到WinSock`10022 ifindex=1500`的原生 FAIL，不能抹掉。
- 原Game函数形参`physical`用于`m0WindowsV4ColdRecordOffer`计算M1 record/MSS预算，H2035直接将其改名`physicalIfIndex`却忘了原recordOffer，Rust/Windows Go编译因此正确拒绝。两者实为独立值：原 OS `selected.physicalMTU=1500`和`selected.ifindex=25`。
- H2037只在`runM0NativeV4WindowsGame`明确**两个独立`uint32`参数** `physicalMTU,physicalIfIndex`。旧recordOffer继续用真实`physicalMTU`，原`m0Plan029TrialCold`传`physicalIfIndex`给Rust Direct socket。原Go caller显式传`physical,selected.ifindex`，无改变Windows物理MTU预算、MSS/FEC、OS/WAL/Defender/TLS和Rust数据面。
- 更新静态回归以同时断言两用途和真实Go manifest两个`create.result_blob` Git blob，禁止再用MTU伪装网卡index。H2037按同一原 Game4 CN四lane物理DNS/FakeIP+Direct TCP/UDP+Tunnel TCP/UDP+双Stop **NOT_RUN until native Action**；旧H2033/H2035所有红灯/NOT_RUN保留。不重新派发共享CDN例外或高压工况。
```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H2037 compile fix for separate Game4 physicalMTU and physicalIfIndex cold arguments, preserving real outer budget and correct WinSock physical binding; source-scoped retest pending."}
```
