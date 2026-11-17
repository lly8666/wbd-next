# PLAN029 H2059｜真 WinForms 用户 flows → 原Go有效值 → 原Rust M1 Npcap 拷贝

在H2055 [真原GUI Action44000778566](https://github.com/lly8666/wbd-next/actions/runs/44000778566) 已通过的**相同原产品入口**上单场增测，而非再跑 H2031 已证的Normal all-Tunnel物理密文Padding。

- commit message必须同时有 `[plan029-real-gui-cn]` 和 `[plan029-h2059-gui-padding]` 才可置测试场`WBD_PLAN029_GUI_PADDING_EFFECTIVE_SCENE=1`。仍为原Normal外层默认1460、内层自动1389、用户CN IP/域分流。原WinForms保存`startup-padding=flows`而非CI从Rust后门硬设；Go`ValidateAsync`读取同键`flows`，原按钮Connect/Disconnect、真实原Go TLS/Rust Wintun OS Applied与内核双出口业务不变。
- 受控STA收集原 Go/Rust Stop消息`WBD_PLAN029_M1_STARTUP_PADDING_NPF_RECEIPT mode=flows copied_records=N copied_bytes=M source=original_Rust_M1_authenticated_NPF_accepted`，要求N/M>0，外部原 E2E 对**同一client.log**验证数值与原GUI receipt完全一致，原生报告Stop/Tunnel UDP+TCP及CN Direct真实业务同步通过；workflow校验当前SOURCE、mode、bytes、Stop，任何漏项FAIL，不凭CLI/config PASS。
- 新源只证明**GUI flows确实到M1/Npcap且应用在场**；逐record随机分布/0..500B真实密文 H2031 历史独立保留不重复。**同一VM off/tls/flows CPU/RSS/p99 A/B**仍OPEN；不引入新Wintun worker/WFP/default路由及新旧Game4/P1/P2范围。

```feature-impact
{"kind":"updated","ids":["gui-config-feedback","startup-flow-padding"],"reason":"One original WinForms native flows selector to Go effective to Rust authenticated M1 NPF copied bytes and owned Stop, without repeating H2031 or claiming off/on CPU RSS."}
```
