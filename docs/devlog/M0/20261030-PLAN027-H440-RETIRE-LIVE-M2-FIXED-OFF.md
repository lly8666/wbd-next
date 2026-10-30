# PLAN027 H440｜退役 Fixed/off 在线逐 record M2；精确源码待验

恢复 main a7c492bea0434670d72ea02b417386c5b7ac8537 / H439，核对在途 Actions：native-functional [40982174181](https://github.com/lly8666/wbd-next/actions/runs/40982174181)、G2 [40982174212](https://github.com/lly8666/wbd-next/actions/runs/40982174212)、governance [40982174062](https://github.com/lly8666/wbd-next/actions/runs/40982174062) 均仅对应 H439 代码/治理，非真实双端 A/B/C；H437 前的原Windows↔Linux Auto 失败和旧源模式证据原样保留。

本批 Windows original owner 不再按 Fixed/off DATA PN 维护旧 RX bitmap，任何模式都不生成 legacy M2 控制页；收到 authenticated kind1 Receipt 明确拒绝，不凭其回收 frozen shadow，保持外层ACK索引的一次可选密文修复和Health/Auto Quality；原严格PN/Seq预检未动。Linux native RX 不再创建非Auto逐record bitmap，TX 只输出到期 Health 或 Auto START/CLOSE/成熟摘要，不依据旧M2给shadow确认，外层原ACK与真实driver预算仍独立。Windows过时回执单测改为负例，非Auto无回执不烧PN/Seq。未更改 legacy独立probe/单测的离线历史协议，并不等于线上仍启用。

**SOURCE未通过新编译/系统测试，不标功能PASS。** 已知§0：①PARTIAL源码候选 ②A NOT_RUN（仅旧组件） ③B OPEN ④C/5min NOT_RUN ⑤OPEN；下步优先收同源CI首FAIL并修，再全体自动进入A/B/C，不为旧M2扩测。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair","fec-auto"],"reason":"Retire live per-record M2 Receipt/bitmap on original Windows and Linux owners for Fixed/off while keeping authenticated sparse Quality/Health and scoped immutable outer ACK/SACK repair; pending qualification."}
```
