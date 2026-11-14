# PLAN029 H1804｜H1803 Windows ABI E0609 与功能卡超限

- H1803 SOURCE `301dddab9a9d371e6065b17be6b23010082e0618` [Windows cross-ABI Action43562854893](https://github.com/lly8666/wbd-next/actions/runs/43562854893) **FAIL** 首错 `E0609: &ResolvedA has no field canonical`：TCP/53 多A闭包变量 a 遮蔽外层 DNS Resolution a。改 `candidate`，保留 DNS `a.canonical` 与候选 `candidate.address/ttl`，不改变 DNS/journal 语义。
- [H1803 governance Action43562854925](https://github.com/lly8666/wbd-next/actions/runs/43562854925) role/governance 绿，但 Feature Catalog 卡片超仓库 16KiB 硬限。精简卡片 JSON，合并过时重复限制摘要，原始 H1669/H1690 失败、H1676 单测及其他 NOT_RUN 保留在验证行和原 evidence/历史提交。
- 两项门禁修正仅纠编译与元数据，不为真实 D3-D5/P1-P2/GUI effective 新增 PASS，也不发新 native 场景。等待本次 SOURCE 自动CI精确结果。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Correct H1803 native TCP DNS multi-A Rust closure E0609 and restore card under 16KiB while historical source evidence remains available."}
```
