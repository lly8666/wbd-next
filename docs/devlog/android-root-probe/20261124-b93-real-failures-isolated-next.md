# B93｜真实故障分层、十组隔离继续

B92 SOURCE `982bad849468b1cb59faaabd3861ab3f4d7c33d7` [Action 45416465988](https://github.com/lly8666/wbd-next/actions/runs/45416465988) 11 SUCCESS/8 FAILURE/5 SKIPPED。真实 RootService [138527036432](https://github.com/lly8666/wbd-next/actions/runs/45416465988/job/138527036432) 前后台同 owner、明确 Stop、Normal→Fixed 冷模式重启 PASS；WiFi loss NOT_PROVEN、恢复 NOT_RUN。七种原 M4 夹具均 panic Rust local V4 SYN MSS not installed before handshake，未进入 TLS；原 TUN 关闭、内核清理 PASS。真实 DNS dummy 修复后到 UID route batch exit255，三组清理 PASS。UID single 超时，内核已有 5501 CN throw 和 selected UID/default TUN；清理 NOT_PROVEN，不算业务 PASS。其他两 UID 未运行。B91 真实 scoped UDP/TCP bootstrap 已 PASS，不重复。

B93 复用正式 Run 的 Rust cold MTU budget、SetPublicV4AdvertisedMSS、deriveMTUBudget，实际原认证两端 record cap；CI-only TUN reader cache FD/O_NONBLOCK、分段日志、owner.Stop defer，UID single/group/all 三个独立 guest。DNS 原 cold batch 提供实际 stderr；物理组并行于其他组的 CI-only exact rtnetlink selector capability probe（空专属 table、ADD/GET/DEL、原 ip printer；非产品 fallback，独立证据）。单独 RootService guest 仅聚焦未验 WiFi loss/recovery、真 NetworkCallback 观察及恢复后手动 START，不重复前后台已通过项。九专项 guest + 一生命周期，fail-fast false。没有降低原认证、M3/PN、MTU/Stop、FEC 约束；不做性能、main 或外部设备操作。全部新 SOURCE 待 CI；peer M4 和 READY 自动恢复仍 NOT_PROVEN。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Record B92 actual lifecycle and kernel results; correct CI cold MSS initialization, isolate UID cases, and capture exact Android DNS rule capability."}
```
