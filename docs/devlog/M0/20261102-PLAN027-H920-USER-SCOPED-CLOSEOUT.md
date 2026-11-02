# PLAN027 H920 | 用户授权限定收口与外层重传登记

本次用户授予M0一次读写并要求按已有真原生结果结束PLAN027。原产品SOURCE `6693910f879f9e55e77dd823c1b05d8942321929` H908不变；本提交只有文档、功能卡与任务指针。无编译、网络Action、物理部署。

五项按计划§7及[机器可读收口证据](../../evidence/M0/PLAN027-H920-SCOPED-CLOSEOUT-20261102.json)逐项有限结算。最后证据：H915 Normal100M同VM OFF CPU16.4062s/ON19.2188s，ON多2.8126s，不称算法优化；H917 Normal ON300s/Auto ON240s/Fixed6 OFF50M均真实双OS/Stop PASS；H916 Game4FEC6 OFF20M250ms30% PASS；H914 GameFEC ON与Normal ON100有原生正例。Fixed50容量约66%单核，停止同族继续盲扩。

原H917 burst Action41424741198是FAIL，原生child/Stop PASS；H918维护Action41427002255因旧游标11refs>8 FAIL，H919治理41427303752 SUCCESS。旧结果不改绿。Windows Auto客户端降档未证、Game总FRC字节与跨OS单向p99未测、Windows全程独立TCP+UDP300s与rotation/GUI/物理不做泛化。项目当前未执行的新MTU统一后移至PLAN027A。

外层重传ON/OFF此前已有独立功能卡 [`outer-opportunistic-repair`](../../features/entries/outer-opportunistic-repair.json)，默认ON回退OFF；Linux `--outer-repair on|off`，Windows真实native cold生效/CLI后端有原生证据，GUI切换/持久化尚未正式验收。卡片增补同SOURCE正例，仍experimental且promotion=null。

按用户授权关闭限定的PLAN027网络验收、登记PLAN027A为PLANNED，不重复dispatch，所有仍有效的认证/原密文/Stop/MTU安全硬门保持。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Refresh previously registered ON/OFF outer repair feature with exact H908 signed Windows/Linux source-scoped off/on/CPU/capacity/long-run evidence and preserve missing GUI/physical/wire-byte limits; docs-only PLAN027 scoped closeout."}
```
