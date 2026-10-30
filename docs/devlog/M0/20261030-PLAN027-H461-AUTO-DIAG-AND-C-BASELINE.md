# PLAN027 H461｜复用真实SOURCE定位Auto饥饿，开启C逐级基线

恢复用户完整任务，取到H460 Auto真双OS Action40996124709 / artifact12951313833：Windows原生业务UDP TX386/RX0，Linux TX89/RX26，Linux Rust M4 TX 40.811s CPU／约42s，native FEC firstsource=9、parity planned9 sent0，真实封包/双方驱动无法通过。H459 Auto CLOSE定时器补丁单元PASS但未改善实际症状，不能从green Core得到B Auto PASS。

H458 A2 real source88ba: Normal10M/250ms/0% Windows & Linux首到100%；30%各约0.70，与线路丢包相符但无单向p99；Normal30 Linux TX CPU61.516s/60s vs Normal0 CPU4.537s/60s。A3真实Fixed10M/250ms/30% Windows first=10.0993%、Linux=99.9377%，Linux TX CPU61.354s/60s且TUN source10280而发包端99551，单核/资源瓶颈阻断Fixed更高同族容量，绿横幅不能掩盖。保留全部原Artifacts与产品缺陷，不把容量当通过。

复用Rust已经存在的 `WBD_FEC_EGRESS_DIAG=1` （仅500ms原生M4聚合，不增加per-record热日志），仅当本条命名Auto实验 scenario 被明确选择时注入原Go Linux服务端启动环境。H461调度只复用H460 **成功构建**的Win/Linux二进制manifest/hash和官方原Go主源码；H460的Auto实测仍是FAIL。一个新Auto25ms/0% Action收真实FEC阶段/CPU/先到，另一个独立Normal10M/25ms/0% Action开始C容量梯度。场景各自一个测量控制job，同源二进制不重复编译。

额外只组装C Normal50/100/200Mbps25ms0及10M/25ms0稳定5分钟，扩大既有V2 240s单场景上限到300s并补300通过/301拒绝的同批单测，**未派更高容量/5min**，以每级真实通过和主机CPU/PSI作为继续条件。A4 120s、A5 CPU AB、B Health/轮换等仍待推进。

```feature-impact
{"kind":"none","ids":[],"reason":"Explicit low-rate diagnostic activation in test harness; capacity scenario fixtures/parser/tests only, no production change."}
```
