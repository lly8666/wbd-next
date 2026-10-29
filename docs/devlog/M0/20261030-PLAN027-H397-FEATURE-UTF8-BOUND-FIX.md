# PLAN027 H397｜修复 H396 功能卡 UTF-8 体积门
2026-10-30。回收 source519a8a6d 的 [governance 40944961891](https://github.com/lly8666/wbd-next/actions/runs/40944961891)：Governance job SUCCESS，但 Feature catalog job FAIL，原因是功能卡必须为有界 JSON；先前按 JS 字符数估计大小，未计 UTF-8 中文字节。未把该 FAIL 当 PASS。
将 fec-auto 卡片尾部 H393/H396 重复状态压缩为同一条，保留 H393 Action 和 source-only 事实、H396 pending 和生产 NOT_RUN；详细原始信息仍在 H395/H396 devlog/证据。H396 native Action40944961945 继续等待，不重复派发。无产品代码改动，不代表 PLAN027 A/B/C 验收。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Compact duplicated H393/H396 source-only limitation to satisfy bounded UTF-8 feature-card gate without promoting unverified live behavior."}
```
