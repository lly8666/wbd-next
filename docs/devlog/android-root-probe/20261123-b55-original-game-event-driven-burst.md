# B55｜Android原Game2/4 M4直接TUN业务突发与idle事件低唤醒

**基线**：`c3f4b828b704b43219d4750f94f901056bf7c347` [Dual64 #45185545494](https://github.com/lly8666/wbd-next/actions/runs/45185545494) 11 SUCCESS/4 SKIPPED，包括原Go/Rust双ABI、ARM64签名APK、Linux双Oracle；原Android真实Game2/4业务与CPU耗用尚NOT_RUN。

- **原Rust热路径**：`v4_android_game_m4.rs`原单TUN→原GameAdapter.offer/drain→2/4真实RAW，不再每个已经排队的App包都单独poll；最多8个包有界内联读写后回到**原事件轮询**，仍每包按原Game4错峰及FEC到期发送，无新缓存队列/线程、M1/AEAD/PN复制或Go per-packet。
- **原Game2/4长寿命低CPU**：原TX与2/4路RAW RX空闲250ms等待改为最多1000ms内核eventfd唤醒。TX计算原HealthClock下一次Health/Dead与原Game4及固定FEC最早deadline，不延误4/50/140ms副本及parity；数据fd或owned Stop eventfd一旦就绪仍立即醒。RX仍复用原真实Readiness、M3/PN/ACK和Stop。
- **同源软件测试**：独立无Android依赖的 `v4_android_game_schedule.rs` 三条Rust例验证idle 1s、Game4/FEC/Health到期优先、8包burst公平与恢复；加入现有 `b2c2b-rust-dns-udp-inverse-map` Host Job，不另开大矩阵；正式APK源码门校验生产调用链。源锁双ABI/签名APK及LinuxOracle按本次Actions验。
- **明确边界**：普通App TCP/53已有原M3隧道透传；物理TCP/53直连需要双向TCP流生命周期，不能由现有物理UDP53/TCP SYN观察冒充。Game2/4真实Android包字节E2E、切网、CPU下降幅度 **NOT_PROVEN**，需同一设备和源二进制实测；不操作真实手机/服务器/main/M0。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B55原Rust Android Game2/4 M4真正TUN→GameAdapter→RAW TX最多8包免逐包poll，Health/Game4/FEC到期优先的1s idle wait、2/4路RAW RX idle1s readiness；无新业务worker/安全控制。"}
```

## B55b｜普通App物理DNS查询也参与现有有界事件公平调度

在上述 B55 Game TX data path 复核中找到实际功能问题：`DnsRoute::PhysicalUDP` 原先向同一 `AndroidBoundPhysicalDnsUdp` 发出真实query后直接 `continue`，**绕开当轮FEC/Game4 due与物理DNS回复fd的poll**。对真实用户多App同时发短串查询会推迟原TUN答复，并非仅极端攻击流量。B55b把这条早退改成 `if PhysicalUDP{...}else{原TunnelDns+GameAdapter offer/drain}`，保证物理查询绝不重复原M3业务发送，又会和普通App RAW业务一起按B55最多8个TUN后回归**同一原物理UDP DNS fd/eventfd**，同时处理Health、Game4/FEC due；无额外工作线程、Socket、DNS代理。源门直接锁住不能早退且不能把物理查询送GameAdapter。B55a旧SOURCE和CI独立保留，B55b新SOURCE另验，Android实机双向与CPU仍NOT_RUN。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B55b消除原Android Game物理DNS发送后continue造成的原物理DNS reply/原Game4-FEC due事件长期不公平，所有原业务共用8包事件短突发，无新worker或协议路径。"}
```
