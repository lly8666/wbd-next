# PLAN027 H429｜FEC2 Quality 分母真实 source，与 parity 隔离

按 H428 双端低频源窗口走查发现原 M3 FEC2 opener 的 `authenticated_data_pn` 为每个 kind2 source/kind3 parity 都提供legacy Receipt；而新 sender 只计真实原source firstsend。若 RX 将parity误计为收到 source，真实received可能大于F，让 v2 report无效并使Auto永不取样。新增纯M3 `quality_source_pn` 字段：已通过AEAD/replay/FixedStream的kind2原source才能增加四窗口 unique bits；Normal LINK有效原记录仍可累计；kind3的认证控制/健康保持，legacy Receipt未改。Windows 仅 kind2 计低频，其他路径继续留旧M2隔离。未新增Go每包调用、加密器或 PN；测试只走Actions。Fixed/off M2替代、A/B/C还没结束。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Prevent FEC2 parity PNs from contaminating authenticated low-rate received-source F denominator across Linux/Windows original M3 owners."}
```
