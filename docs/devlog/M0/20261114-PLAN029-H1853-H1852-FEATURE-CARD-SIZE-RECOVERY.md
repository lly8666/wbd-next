# PLAN029 H1853｜修复 H1852 功能卡16KiB治理界限

H1852 `df26d8c6` 首个feature catalog失败为卡片17271B超过16384B，不是已证明Npcap修复的实网失败。仅将重复的限制说明压缩到16287B，保留全部41项验证SOURCE、evidence、失败、NOT_RUN和experimental标记，未放宽既有治理。新commit不带P2场景marker，不重复派真实网络；H1852签名SOURCE在途，结果待收。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Fit existing 16KiB feature-card limit without deleting or promoting any source-locked verification; no new product or network scene."}
```
