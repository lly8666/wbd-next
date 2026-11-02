# PLAN027A H966｜接收预算真正的固定1360残留+隔离冻结测试

H964生产`DefaultMSS=1360`常量删除后，[Windows编译41475929919](https://github.com/lly8666/wbd-next/actions/runs/41475929919) 和[原生WAL41475930020](https://github.com/lly8666/wbd-next/actions/runs/41475930020) 首错都指向原Go `internal/datapath/handoff.go` 第105/201行：Client和Server真实RX方向仍使用 `faketcp.DefaultMSS`。本次正式一套源用Rust冷预算已安装的当前`PublicV4AdvertisedMSS()`替代，TX方向继续保留原对端`PeerTCPProfile`，不能用本端MSS发送。正反方向原Go真实源码与原测试完整overlay到两个精确manifest，绝无旧版本兼容开关。

[H965 Windows ABI41476643366](https://github.com/lly8666/wbd-next/actions/runs/41476643366) 因冻结旧M4 ABI仍复制共用原Go TLS测试，而该测试调用新current setter失败。恢复通用测试，在PLAN020独立stage阶段才加唯一源锁的`_test.go`1420初始化；Linux当前原Go测试已有相应显式测试值。遗留datapath单元测试同样有仅测试构建的显式MSS1420，不影响正式Go程序。H965治理41476643027因cursor 8288B超过8KiB，改成短摘要并保留所有旧证据原文件，新的cursor 3150B。

H966 fresh SOURCE真实Windows/Linux MSS1420、record和两端TUN/Wintun1389仍**NOT_RUN**；需编译后才能验证。H958 DF失败保留，028–030暂停。

```feature-impact
{"kind":"updated","ids":["path-mtu-budget"],"reason":"Remove two actual receive-path DefaultMSS1360 dependencies, unify Rust-installed local MSS and source-locked Go Windows/Linux, isolate frozen test setup and cursor budget."}
```
