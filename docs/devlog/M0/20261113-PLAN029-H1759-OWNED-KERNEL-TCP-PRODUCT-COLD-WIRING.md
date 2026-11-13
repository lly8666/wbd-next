# PLAN029 H1759｜原始产品同一Wintun的Rust kernel Direct TCP两阶段接线

- H1757 [Action43442086701](https://github.com/lly8666/wbd-next/actions/runs/43442086701) 单精确Defender Allow Add/Readback/owned CAS真机PASS_SCOPED，非产品TCP PASS。H1758治理Action43443234834已绿。
- 本批把原Rust V3冷态PREPARE/ENABLE接入原始凭证验证Go产品。仅在全四阶段OS实际Applied、路由同一代synthetic /32已写入owned WAL后，向原Rust TX发PREPARE获取真实本地TCP端口；保存精确源/目标/端口单规则owned Defender intent+readback，**仅成功后**Rust ENABLE；Stop先按本代owned CAS删除防火墙规则，再复原routes/DNS/MTU/lease和停止Rust。未确认intent保留WAL、不虚标Stop；不引入旧WFP、smoltcp或第二Wintun。
- synthetic 198.19/16由installation+epoch哈希生成，非固定探针地址，与198.18/16 FakeIP分离。all Tunnel不分配Direct TCP。原V2非试验入口未提升产品029成功；原owner/认证/MTU/外层TLS不变。
- 本次只为源码与纯单元编译，**新SOURCE还没签名双腿TCP回包或D1–D5/P1–P2**。先收已有auto Actions后才作完整实网场景，失败按首个边界定向修。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Original authenticated Go Rust kernel TCP postApply prepare-owned Defender-enable-Stop source wired, not yet native network verified"}
```
