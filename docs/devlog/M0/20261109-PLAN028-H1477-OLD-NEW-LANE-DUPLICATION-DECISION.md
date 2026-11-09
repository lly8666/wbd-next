# PLAN028 H1477｜老版 Game 双副本≠跨 generation 轮换双发；原样本 TUN 待发队列排除

读最新 main `857fbfcd3492`、M0 cursor、源锁 `66fb6b44...`、原[H1473 Action42595013191](https://github.com/lly8666/wbd-next/actions/runs/42595013191) artifact 13663646307 原始 ZIP（SHA-256 `fdae6e22edb906bd09c84e015012402457b9193afeaed4643f42e6f5e989cbe8`，ZIP CRC PASS）。不是新原生测试，不改变产品 SOURCE；原 rotating12 Alice DL13/Carol DL3 FAIL、static12全方向零缺 PASS、其它受限范围原样保留。

原服务端 shared-TUN 终态：rotating Alice offered331225/direct331225、pending_peak0、pending_overflow0，整个 reader retired_drops0、queue_full_drops0、queue_age_drops0；static offered330143/direct330143、同样零队列丢失。因此 `enqueue_shared_tun` 在 route 改代时抛旧 pending 队列这一候选原因 **NOT_TRIGGERED / 排除本次原样本**，不能解释 Alice 的缺包；不能据此擅自加容量或开启双发。客户端原 M3 rotating delivered331210、static330143，但含多类包，不能和 UDP 应用丢失逐包一一对应。

同一 CLOCK_MONOTONIC 第一条新代 500ms M4 采样：Gen2 server/client `196173154687 / 196180153649` ns（差约7.0ms），Gen3 `289634298393 / 289642693610` ns（差约8.4ms），双方届时均已处理大量包。原 H1476 约515/517ms 是丢失起点到“首个500ms采样”，**不等于客户端 B 晚服务端 B 就绪半秒**；仍须捕捉真正 FIRST RAW TX→client RAW RX→AEAD/replay→M3 TUN 的第一差分。

旧仓库 `lly8666/wobuzhidao` 的 [Game WrapCopies/Decoder.Add](https://github.com/lly8666/wobuzhidao/blob/dev/wbd-raw-fec-v2/internal/gamelane/gamelane.go) 是同一 logical PacketID 多 lane 复制并去重，证明 Game 业务冗余，不证明 A/B **跨 generation** 随机时长双发；旧跨代方案未在所查源码得到确认。现行 [path_supervisor_linux.go](https://github.com/lly8666/wbd-next/blob/main/r0/go_overlay/internal/v4productcli/path_supervisor_linux.go) 已有随机10–20s **旧 RX grace**，但共享 TUN 一条生效 TX route，Server 新代发布后精确退休旧代。不能把上述三种语义混为一谈。

决定：本轮**不改产品、不新增 wire、不开全业务双发、不 dispatch 重复原样本**；唯一下一步是容量内12Mbps短原生 bounded FIRST-stage 观测，区别 server RAW kernel TX / client RAW socket RX / crypto replay / TUN 交付，并检查停止前旧代在途工作；如确认交接边界故障再做最小修复与受影响回归。PLAN028 **IN_PROGRESS**，保留原 FAIL 和 Windows/物理/Android 未验。

```feature-impact
{"kind":"none","ids":[],"reason":"Original artifact offline readback, legacy historical comparison and fault-hypothesis exclusion only; no product/config change."}
```
