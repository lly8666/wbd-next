# B56｜原Android Game2/4 M3接收短突发与事件驱动长空闲等待

## 固定证据
起点 `2f3a02766796a9eed313102417e82b7a60664412`，[Android Dual64 #45189246018](https://github.com/lly8666/wbd-next/actions/runs/45189246018) 11 SUCCESS / 4 SKIPPED，双ABI、arm64签名APK、原Linux两个oracle和DNS/CN/M3 Host成功，实体Android应用双向E2E及CPU测量仍 NOT_RUN/NOT_PROVEN。保留前序B55/B55b全部实际证据，不回写原FAIL。

## 本轮批量生产改动
- 原 `v4_android_game_m4.rs` 的 **2/4条原生RAW RX** 每条原M3 record完整读入后，原`GameLaneOpener.open`→原Game FEC或GameReceiveOwner/PN/replay→原TUN写回→ACK逻辑逐包保持不变；但有已排队的RAW包时，最多连续处理8条后再回到同一`AndroidWorkerWake` 轮询 Stop。这样不必每条合法包都重新poll(2)，没有新TUN reader、per-packet Go/JNI、处理线程、数据排队、AEAD重封。
- RAW RX worker无Health/FEC/Game4定时任务。**原 idle 每1秒自动醒**改为最多30秒的同一内核fd+eventfd等待；实际RAW就绪和Go/Rust原Stop信号依然立即唤醒，并不增加用户业务时延。Game TX独立按原Health/Game4/FEC deadline最多1秒等待不动，B55b物理UDP53回复公平调度不动。
- 复用B55 `GameTunBurst` 纯数字调度器，不产生额外数据复制；追加两条Rust Host用例分别检查RX有界短突发/空TUN恢复以及事件驱动idle上限，沿现有 `b2c2b-rust-dns-udp-inverse-map` Job按新SOURCE自动运行。
- 为实际持续产品开发，原 Android Dual64 工作流**补上Game Rust文件的路径触发**，并在既有App源锁检查同样源码；不增加新Job或主动重复dispatch。所有编译/Host软件PASS均不得冒称Game2/4真机M4双向或性能提高。

本批继续不做不必要防御/攻击篡改支持、不去搭另一套Android TCP53协议栈。现有App TCP53已走原M3透明隧道，物理TCP53独立代理要真正拥有应用内层TCP会话，Windows的内核TCP listener不能直接代替Android TUN RAW分段。main/M0不修改、实体手机或联网服务器不操作。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B56原Android Game2/4每条M3 RAW RX worker直接连续处理最多8条原AEAD/PN/TUN/ACK记录减少逐包poll，空闲事件等待1秒→30秒仍由RAW与Stop eventfd即时唤醒；原工作流加Game源码触发并复用Host验证。"}
```
