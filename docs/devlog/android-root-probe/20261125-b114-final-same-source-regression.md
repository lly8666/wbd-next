# B114｜最终同源普通业务回归，停止扩大功能矩阵

B113 SOURCE `e4bdc007ffcaf3345e67c60b8122717591af513c` [Action 45571116221](https://github.com/lly8666/wbd-next/actions/runs/45571116221) 13 SUCCESS / 0 FAIL / 9 SKIP。Auto [139059755881](https://github.com/lly8666/wbd-next/actions/runs/45571116221/job/139059755881) 五轮TCP/UDP 40+40、5MiB/方向、9702实际payload帧/drop97，原Android M4 source_raw5429 parity_raw3724 source_tun4760 recovered_tun76 unique9522 reports4 signals9 mature4 applied1，原Stop通过。B112 Fixed原恢复交付77、reports4 mature4 applied1已证。二者不是丢帧恢复率，不宣称Auto全部升/降档轨迹或每个Game恢复候选归因已经证明。生产自动重连 [139059755852](https://github.com/lly8666/wbd-next/actions/runs/45571116221/job/139059755852) 首连接真实业务、WiFi丢失原Stop、原handle 432902426637→437197393933、CI carrier重挂、无第二外部START、真实第二认证/READY及App业务/Stop全部PASS。ARM64 signed APK/Host wiring和B61/B62 source audit [139059052814](https://github.com/lly8666/wbd-next/actions/runs/45571116221/job/139059052814) PASS；[139059492915](https://github.com/lly8666/wbd-next/actions/runs/45571116221/job/139059492915) 仅host admission，KVM_NOT_ACCESSIBLE，未运行ARM64 Android。

B114 只执行一次收口的同源回归：B112曾改变生产Go/Java冷控制及原生FEC读回，因此旧SOURCE七模式PASS不能替代最新SOURCE回归。8个独立guest共享一次同源构建；Normal显式隧道UDP/TCP DNS relay，Normal生产WiFi自动恢复，Fixed和Auto真实1%下行轻损五轮业务+恢复TUN+reports/mature/applied非零（将既有观察提升为最终验收门），Game2、Game2 Fixed、Game4普通双向，Game4 Fixed真实轻损及恢复候选/业务。复用现有真实TLS/lease、原Rust M4、普通App TCP/UDP、字节校验、Stop；不添加生产代码、热路径、故障注入种类、参数矩阵或测试专用产品逻辑。不再重跑其他已通过组件或非产品Linux普通TCP carrier历史FAIL。

通过则x86 CI大类限定范围收口，不继续为测试数量扩展。尚未独立证实Game每个恢复候选最终写TUN，不能宣称精确Game FEC恢复率；实体ARM64 ISA-L运行、物理RAW对端、实际热点/IPv6/切网、真实吞吐/延迟/CPU/内存仍需授权真机；CI ADB carrier不作为物理性能证据。治理两workflow历史FAIL保留，main由M0独立推进，PR36 Draft，未合并或操作外部设备。B114新SOURCE待CI。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Accept B113 Auto recovery and production automatic reconnect, freeze one final same-source seven-mode regression with existing ordinary scenarios."}
```
