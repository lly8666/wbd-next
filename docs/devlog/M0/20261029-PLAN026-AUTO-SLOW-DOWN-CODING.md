# M0｜PLAN026 Auto 缓降应用到现有唯一 FEC2 策略（源码候选）

- 2026-10-29 同 M0 main task/epoch；源自旧 `wobuzhidao/internal/adaptivefec/controller.go` 稳定约30s后一次只降一级的行为，现行 `FecV2Step` 与成熟2s/8s Rust M2事实不变。
- `fec_v2_policy.go` 把真正的 down proof 持续时间及相邻降档间隔由10s调为**30s**；依旧需至少5个不同的可信2s窗口、4096个有效源、actual-k、非HOST_CAPACITY/UNKNOWN和真正Applied。HighFastWindows>=2的快速升档路径不动。低PPS无可信样本不假降。
- 同步更新已有长程/间歇UNKNOWN/k偏差 Go回放测试的虚拟时钟，未执行；Windows最终由Rust唯一actor取代Go steady policy时应对照这套成熟行为，不复制Go ticker。用户接受正常足量业务两分钟内一档；30s hold保留重传/真实关闭节奏裕量。
- **只修改策略候选及测试，无新网络/性能/物理PASS；不触发手动产品矩阵。**

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Normal Auto缓降门槛由10s调整为30s，旧FEC2能力仍为experimental、未授权按文档声称新网络PASS。"}
```
