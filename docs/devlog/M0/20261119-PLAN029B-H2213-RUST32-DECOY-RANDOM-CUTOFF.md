# M0 H2213｜Rust native槽16→32＋普通非WBD TLS/Decoy独立随机超时

**2026-11-19；当前代码阶段 IMPLEMENTED_TEST_PENDING，未拿到新SOURCE原生CI结果前不写PASS。**

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
