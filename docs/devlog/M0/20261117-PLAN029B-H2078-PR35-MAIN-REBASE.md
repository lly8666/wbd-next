# PLAN029B H2078｜PR#35 非冲突内容合流

用户2026-11-17明确授权重新接续029B。PR#35 `ce3c6c53`（旧base `601d5404`）是12个纯文档/功能卡变更，GitHub不满足直接merge。已在主线 `a2431abeeb22f7d556a7d03b6bd099f88ce1d838` 合流全部可独立保留的029B方案、固定提示词、029/分流契约增量及分包入口；原来未触及的文本采用PR版本，主线上后补的H2077日常三场signed Normal真业务PASS_SCOPED、旧FAIL/NOT_RUN保持，功能卡只加doc ref和029B设计待验，不用旧PR整文件回滚新证据。START_HERE加当前用户授权状态，原保留M0单写与SOURCE优先。

**029B生产代码没有在PR中实现，本提交不声称 B0–B5 或新GUI/IPv6真网络已经合格。** 按 `docs/prompts/M0-PLAN029B.md` 继续在同一main实现，冻结全链后才受控build＋最小有界Windows2025/WSL2签名原生代表＋同VM性能保护；不重启028/030、不会无意义重刷旧网测。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6","gui-config-feedback","startup-flow-padding"],"reason":"PR35 029B design rebase with H2077 verified newer feature data retained; product tests remain NOT_RUN"}
```
