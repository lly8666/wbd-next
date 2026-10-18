# M0 R0-023｜真实原 TUN jumbo / LINK owner 持续批次（未验源码）

任务权威：main registry rr=2、M0 epoch=1、R0-M0-V4-PROTECTED-OWNER-COMMIT-023。起点 H161 `1102dccf93d9fbd6f75da6c750ce05f6220369e3`，checkpoint `8d7212a1b1bf68292b0b8fd812543099271dbe27`；此前精确通过的源码仍是 `a474def3562eab434d8619ba6207d2088cf63631`，不可把它的 PASS 转移到本改动。

## 本次代码改动（pending SOURCE verification）

- 在 M0 原本的 `background_tun_once` 增加一份重用的 65535B TUN 接收缓冲区，避免 Linux TUN read 在 M1 2048B slab 上不可恢复地截断完整 IPv4 jumbo；小包仍复制进入原 generation-scoped M1 Arena、原 Rust owner、原 M4 kernel，其他工位文件不改。
- 有界队列最多四份待发完整大包，外加最多一份活跃 source；活跃 jumbo 固定 generation、LINK packet ID、原始 frame MTU 与路线事件 revision。跨 TX wakeup 续发一轮最多 32 片，原始 M3 LinkPacketPlan 每次重新构造并跳过已发行下标，不重授 AEAD/PN。只对当前已证明 copied 的 prefix 推进；任意 partial/Uncertain/Stop/MTU shrink/事件失效丢弃剩余同 ID 尾部，不改 stride。
- 每次 TX 轮先处理现成小包再发剩余 jumbo，完成后在没有新 TUN readiness 时仍立即处理待发剩余批次；保留每轮上限 32。
- RX 新增 pending 与 invalid 的区分，认证通过的 LINK 分片未重组不是 RX 失败；原 M3 malformed/discarded 与真实 TUN sink 写失败仍失败。
- 新增 M0-only 65KiB 持久 owner source / 32+16 / M3 重组 / loan / MTU shrink / Stop-native 功能断言，并纳入现有源锁定 CI。

## 尚须验证的边界

当前提交是候选实现，不宣称源 PASS。真实 Go credential TLS → Rust original owner → M1/M3 → M4 raw/TUN → peer 重组 65535B 的端到端测试需在同源 Actions 观察。M4 实际 kernel partial/Uncertain/Stop/MTU±1、跨 generation 与产品级无 HOL/效率回归还须证据；一次 jumbo 接收改为重用 65KiB scratch 且小包多一次 copy，性能资格 `NOT_RUN`。真实 Go CLI/GUI applied 修订、2s 自动反馈、M2 反向认证 kind1、全平台及物理机、240s D10/p99、历史 150ms 红灯均未关闭。**产品 FEC2 OFF。** 旧 PASS/FAIL 原样留存。

下一步：按这次 SOURCE 真实 Actions 的 run/attempt/工件核对构建和新增反例；修复后才记录精确证据 S，最终单独 cursor-only H。
