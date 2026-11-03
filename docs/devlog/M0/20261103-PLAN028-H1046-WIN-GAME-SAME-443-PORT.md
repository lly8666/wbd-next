# PLAN028 H1046 — Windows Game 二号 lane 冷建链超时的根因修复

H1043 Windows 原生 [Action 41648749762](https://github.com/lly8666/wbd-next/actions/runs/41648749762) 确实 FAIL。其原始工件 `13237431073` 中 Game2、Game4 和 FEC 子场景均重复发送第二lane SYN，Linux Game 服务端只监听/接受目的443；Normal/Fixed/Auto单lane则通过。

**根因（SOURCE读回）**：`runM0NativeV4WindowsGame` 中 `src,dst := SourcePort+i, ServerPort+i` 错将多lane服务器目的端口从443增长为444/445/446。Linux 原Go服务器明确只接受单端口443；这违反028单入口和客户端不同本地端口同服务端口的要求，不是时间预算问题。现将目的端口固定为配置的ServerPort，本地源端口仍按lane区分；原 `NpcapEndpoint` filter/SYN 与 `ClientFlow` 共用同一纯冷helper。加Windows原Game编译标签下4-lane / 443、8443 / overflow单测，不增重试、逐包路由头或Go热循环。

本改动先标 **SOURCE候选、实际Windows双OS Action尚未出结果**；不把Linux H1044结果顶替Windows Game。保留H998在线MTU收窄FAIL、ARM64 Game4FEC FAIL、远端ICMP未测、CPU因果未证与Windows真物理切网NOT_RUN。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1046 fix exact Windows Game multi-lane outbound dst-port fanout: all independent source ports now reach the ONE original Go server port; cold SOURCE native Action pending."}
```
