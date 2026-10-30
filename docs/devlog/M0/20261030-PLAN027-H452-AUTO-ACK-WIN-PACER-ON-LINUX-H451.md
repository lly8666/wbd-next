# PLAN027 H452｜H451 Linux上叠加真实ACK、Auto口径、Windows及预算修复

恢复期间main已到H451 Linux commit 7c9dbe31；先前离线Git对象a761c40c没有进入main。本次以7c9d作base快进，不覆盖Linux已完成的Fixed真实FixedStream安装读回、Auto有限窗口和失败CLOSE 500ms重试。补齐Linux worker的low_next实际无新firstsend不设过期deadline。

Windows/Linux生产outer_ack当前都喂空SACK；新增三次合法累计重复ACK且确认存在后续真实firstsend并超过20ms reorder守卫后，最多提名首个冻结密文候选。仍由shadow一次原密文/PN、实际driver以及全局R<=0.10F约束，不得当业务交付。stage0从8MTU平滑令牌桶取额，替换旧21发瞬时断言。

Windows Rust Auto与Go策略将真实独立采样F丢失率及全量闭块actual-k分布分开：k仅按自身cohort归一化，不除抽样F误判不匹配；样本>=64保有限有效统计，空反馈/k继续UNKNOWN。Windows Fixed不发收多余START/CLOSE，固定/自动readback以实际安装FixedStream自身revision/profile为局部Applied事实，旧M2收据统计不再门控。原Windows Fixed bitmap RX及无消费者per-DATA MatureFirstSend热feed停用。新对应源码反例、Go测试及两个功能卡更新。

本批尚未得到同SOURCE原生/真双端Actions或新性能数据，保留H449 Linux短测试原SHA成功、ec1c真实双端FAIL；A2-A5、B完整生命周期和C/5分钟并未完成，继续推进。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair","fec-auto"],"reason":"Live 3-dup ACK one-shot and stage0 pacing, independent sampled-k Auto, Windows Fixed local Applied; Linux H451 preserved."}
```
