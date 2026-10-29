# PLAN027 H418｜Linux 非 FEC2 build 保护

H417 NORMAL-COMMON Action 40969611046 FAIL：LinuxQualityRx 类型受 fec2_product_record 编译开关保护，Entry 新状态字段及初始化遗漏对应 guard（E0412）。本批将四处新增 field/init 按原可选 feature 门限定，不改变默认 Normal/off 实现或操作语义。待 H418 真 Action 编译与测试，历史 FAIL 保留。Linux 发送窗、Auto 模式、全部 M2 退役及 A/B/C 仍 OPEN。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Fix Linux non-FEC2 optional quality state type/fields compilation gate after actual Action E0412; no behavior change outside selected feature."}
```
