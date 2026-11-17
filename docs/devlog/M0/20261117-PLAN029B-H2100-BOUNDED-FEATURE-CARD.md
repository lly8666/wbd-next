# PLAN029B H2100｜原功能卡16KiB硬上限，保留所有历史真源验证

H2099 SOURCE `19398cc24386a42a702cceb66e25135945c71b88` [governance Action44080799703](https://github.com/lly8666/wbd-next/actions/runs/44080799703)：Governance PASS，Feature catalog **FAIL**，唯一首错`feature card must be bounded regular JSON`。原卡已16,370B（16,384B硬限），增补H2098 signed验证后17,035B；不是产品网测FAIL。H2098原产物Action44078530417、artifact14327500131的PASS依然成立，单DNS两出口真实共享海外A、双向TCP/UDP与owned Stop证据不改。

H2100只修改原卡容量：将已不适用的`CN Wintun未跑`（null SOURCE/NOT_RUN）占位**替换为**H2098真实Normal普通CN同源签名验证；保留所有此前有真实SOURCE的PASS/FAIL verification及其evidence路径、IPv6全局NOT_RUN与高级FakeIP在limitations中明确NOT_RUN。裁去三条仅供旧索引的通用/历史doc_refs（原文件仍存在，不删除任何原始日志或证据），收短summary/defaults。源码/ABI/功能开关均不修改、不额外触发Windows签名测试。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Bound original feature card under 16KiB while preserving all real historical SOURCE verification records and the exact signed H2098 ordinary CN evidence; no product changes"}
```
