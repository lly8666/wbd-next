# M0 H2213｜Rust native槽16→32＋普通非WBD TLS/Decoy独立随机超时

**2026-11-19；H2213 本次小任务 IMPLEMENTED / PASS_SCOPED。产品SOURCE见下方同源四组Action；PLAN029/029B整体技术出口仍OPEN。**

用户明确小任务：（1）Rust承载槽从16调整至32并简单测试。（2）非WBD普通客户端通过WBD服务端的Decoy回落，增加随机连接存活时间，期限到主动结束，不能长时间消耗系统资源。

工程边界与施工：
- Linux `v4_embedded_go.rs`及Windows `v4_windows_owner.rs`源码`MAX_SESSIONS=32`，shared/native多lane容量边界同步；原Rust M4/M1/数据路径完全不变。Linux混合Normal/Game冷管理32 native lanes + Decoy最多8，原FakeTCP冷表从32改为64（不是64 WBD名额）；Log同步如实展示native32/cold64，旧已验收H2212仍保持原SOURCE525证据。
- 原P2真实`FallbackFromHello`继续原同一ClientHello连接、固定origin和64MiB每向限额；在新V4普通访客分支才独立随机15..45秒(crypto/rand)，同时传入ctx超时和原P2两个socket期限；到点关闭旧FakeTCP association，Decoy额度释放，不触碰已识别WBD TLS。旧H2212最大8个普通转发独立额度不变；短于随机上限的已有内测固定fixture期限生效，随机数失败保守取15s。
- 源码锁Go单元：真实stdlib TLS1.3与旧P2目标完成TLS/应用数据交换后**保持连接故意不关闭**，服务器按更短fixture期限主动关掉关联、Decoy槽归还、0 Rust transition；随机15和45端点及采样范围断言，原WBD认证/错误SNI/8名额占满回归。
- 源码锁Rust：Linux32槽及第33槽拒绝路径，Windows使用原native allocate真实依次32个prepared owner、第33个`FULL`。原生产品ABI构建和最小代表性的Linux短Key+Decoy真实网络回归由CI确认后再写证据；不声称32完整真实客户端并发/性能。
- 不改变Android/OpenWrt代码，Java JNI和真实路由器设备、外部公网NAT/DNAT、16→32满载长测及p99均尚NOT_RUN，029/029B整体技术出口OPEN，030未开。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H2213 increases Linux and Windows original Rust native owner capacity from 16 to 32, expands bounded Linux cold FakeTCP association table to 64, and imposes independently randomized 15-45s hard cutoff on ordinary TLS Decoy splices only."}
```

## H2213 第一轮新源CI与冻结旧场景测试夹具隔离

SOURCE `38e92ad9bc532f7bda0f6ffb084c3b600c528ba2`：Rust Linux+Windows[Action44446847868](https://github.com/lly8666/wbd-next/actions/runs/44446847868) **2/2 SUCCESS**，Windows确实依次实际allocate32个原Rust prepared owner并验证第33个FULL（未实际启动32个kernel M4/业务）；Linux真实编译并测32/33 cold限额。原Go Decoy和Linux Rust动态链接[Action44446847713](https://github.com/lly8666/wbd-next/actions/runs/44446847713) **2/2 SUCCESS**，`TestH2213OrdinaryTLSDecoyHardCloseReleasesQuota`用真实普通stdlib TLS1.3→老P2目标完成ping/pong后故意保持TLS打开，在缩短到600ms的fixture限制下服务器主动断开并归还8槽中的1槽；独立15/45秒端点和64次随机范围测试PASS。该短测只验证真实超时路径，不假称线上随机15–45秒已在物理公网长跑。

历史固定二进制兼容性：旧PLAN028 H1072 [Action44446847591](https://github.com/lly8666/wbd-next/actions/runs/44446847591) 原二进制源`d7bd355...`经原TLS/TUN/UDP 5包成功，却因主线公用脚本唯一检查了新日志cold64/native32而在Stop后错误FAIL。只改这个**共享fixture**：H2212开启时严格要求新Rust32/cold64；其他原冻结路径仅接受已知的旧16/32或新32/64这一对互斥合法日志，不把旧冻源宣告Rust32。二客户端旧脚本同样仅接受这两种固定组合，恢复冻结证据独立性，不修改任何Go/Rust产品代码或线上随机期限。

## 最终验收 / H2213 证据

产品同一SOURCE `38e92ad9bc532f7bda0f6ffb084c3b600c528ba2`：Linux与Windows Rust32边界/Windows真实32个prepared owner并拒绝33rd [Action44446847868](https://github.com/lly8666/wbd-next/actions/runs/44446847868) **SUCCESS**；Go原本的P2同端口Decoy真实TLS测试[Action44446847713](https://github.com/lly8666/wbd-next/actions/runs/44446847713) **SUCCESS**，包括普通TLS1.3真实app ping/pong后源站刻意不关连接、采用fixture短600ms期限服务器主动终止并归还普通TLS并发槽；随机15与45s边界和多次抽样PASS，真实生产15–45秒没有等待45秒公网长测。真实Linux原Go双端/内核veth/TUN/AF_PACKET + Rust ISA-L、短RouteKey cache重新启动、443普通TLS decoy、TUN UDP Echo/Stop [Action44446847738](https://github.com/lly8666/wbd-next/actions/runs/44446847738) x86_64和ARM64两个原生作业均**SUCCESS**（各2次完整启动）。冻结旧编译H1072因公用测试脚本日志预期误FAIL后，仅修测试fixture提交`6ba04041e8f0ab1a7a5f0e27e654d556a9812e87`，[Action44447691338](https://github.com/lly8666/wbd-next/actions/runs/44447691338) **SUCCESS**，源码冻源仍为旧Rust16/Go32，不改历史事实。

**未测边界**：32个真实WBD同时在线及混合8个普通TLS长时压力、p99与内存峰值/公网NAT、Android JNI/OpenWrt实体。Rust Windows32个prepared owner验证不等于32个Wintun业务实例；Linux32槽/33rd边界是源码锁条件测试，不冒充32真实联网会话。详见[独立同SOURCE证据](../../evidence/M0/PLAN029B-H2213-RUST32-DECOY-RANDOM-15-45-LINUX-WINDOWS-SCOPED-PASS-20261119.json)。
