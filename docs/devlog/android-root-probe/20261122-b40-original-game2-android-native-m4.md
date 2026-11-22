# B40｜原Game2/off Android Rust M4 单TUN双RAW worker

## 实际产品工序

B39已经将原Go经TLS验证的两个原Game独立lane组合进同一个Rust `GameAdapter`，绑定一张用户选定的Bionic物理Network上**每条lane精确5元组**的原RAW RX/TX。B40不是再建Go转发或独立Crypto，而是新增独立于Linux OS syscall部分的 Android Rust Game2/off M4 kernel worker。

- 同一Go来源的TUN FD在原 `AndroidOwnedTun::adopt` 里验证并迁移到一个原Rust Game TX读线程；其 `GameAdapter.offer/drain` 原M1 frozen TX/PN/AEAD经共享 `ipv4_tcp::build_bytes` 与已选Network的 `AndroidBoundRawTx.send_built_outer` 发往原FakeTCP peer端口，真实sendto成功才推进原每lane TCP seq/copy计数。
- 两个独立 `AndroidBoundRawRx.read_original_record` 非阻塞工作线程各自**移动**原Game `GameLaneOpener` 所持原M3/replay，进入一个共享 `GameReceiveOwner.prepare_opened_receive` 去重预留；反向业务目标仍须匹配保护Go /32，原TUN成功写入后才 `finish_receive(...,true)`，并推进原 `NativePresentationAck`。
- 不增加Go DATA FFI；原 `HealthClock` 的加密kind0及TUN readiness eventfd沿现有worker运行，不新建第二线程定时器；组件有实际的M4数据面计数入口，但没接原Go双TLS前不会由App调用它。
- 同组 `game_group_stop` 先等待Game2 TUN/RAW线程退出、归还TUN borrow，再停全部per-lane RAW sockets，最后原GameAdapter；失败不能报Stop成功。组级真实worker `is_live` 才可让 `game_group_state.drivers_installed` 置1。Game4和Game FEC2仍拒绝此worker启动。

## 严格资格边界

这是 Android Game2/off **M4 worker source**（要以本B40 SOURCE Rust Android交叉编译及Host源码门证明），不是原Go Game2 Native双TLS客户端启动或手机流量E2E。原Go Android当前仍只构建 `wbd_v4_embedded_go`，Root App也只有 Normal/Fixed/Auto，原UID route/Go multi-association/真正服务端双向确认未连接；**Game2仍不可用**。B40无任何实体安卓设备权限/运行，仅CI正常软件门。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B40将B39真Game2冷组复用为同一原Rust GameAdapter的Android单TUN双RAW M3/M4工作器，功能仍不对App开放。"}
```

## 同SOURCE软件收据与关键边界（2026-11-22）

B40生产源码 `9ba1d39f82c424039bbc5940a1de392f159bbca4` 的 [Android Dual64 #45031248129](https://github.com/lly8666/wbd-next/actions/runs/45031248129) 已完整 `completed/success`：`arm64-native`、`root-arm64-app`、`linux-original-server-normal-off`、`linux-x86-original-server-d2-s0`、`original-m3-wire-oracle`、B1/B2 DNS等与`arm64-cuttlefish-host-admission`合计 **11 SUCCESS**，Android x86/KSU native/NativeBridge/D2/TAP四个诊断 **SKIPPED**。独立 [Feature catalog #45031248185](https://github.com/lly8666/wbd-next/actions/runs/45031248185) SUCCESS（Governance Job SKIPPED），[B39d静态回归 #45030552833](https://github.com/lly8666/wbd-next/actions/runs/45030552833) SUCCESS。

**准确解释：**B40新增Game2/off Android Rust M4的生产源文件通过交叉编译和符号检查，但目前仍是**未被原Go Android Game2双TLS产品调用的worker**。原Linux Normal/off Oracle成功验证未回归；Cuttlefish宿主PASS不是Android guest TUN/RAW。原Game2客户端未在真实Android设备完成双lane TLS、服务端真实回包、M3双lane成功计数、App UID路由和Stop，也没有CPU/RSS/带宽验收。上述设备及业务场景均为NOT_RUN/NOT_PROVEN，不能继承正常模式之前的历史真机证据。
