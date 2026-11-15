# PLAN029 H1918｜修治理元数据，H1917原生测试不重发
- H1917提交 `fbff58c923dedec097e976820b832114ff673e23` 的自动 [governance Action43712621086](https://github.com/lly8666/wbd-next/actions/runs/43712621086) 是**真实元数据约束失败**：M0 cursor `context_refs` 由8多插入到9，功能卡 JSON 文件超过16KiB；均不是用户允许忽略的外部假红。保留本次4MiB原生真实故障记录，不因治理失败推断产品通过或失败。
- H1918把 `context_refs` 压回8个最新相关上下文；功能卡移除H1917新追加、重复占位的两行，将H1916真失败/H1917尚未验明确留在短summary；详细原生证据在 `docs/evidence/M0/PLAN029-H1917-H1916-TRUE-4M-REPLY-STALL-20261115.json`，历史验证行一条未删。功能卡 JSON UTF-8大小 16335B，合约上限16384B。
- 此批不改原始产品代码/夹具；已经运行中的原生Action43712621017和组件Action43712621090必须按**原H1917确切SOURCE**回收，不能通过另外dispatch冒充同机测量。后续同VM旧新二进制CPU A/B及Direct小流延迟仍待施工/实测。
```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Compress feature card within 16KiB and keep H1916 real 4MiB failure and H1917 pending summary; full evidence is separate and historical verification untouched."}
```
