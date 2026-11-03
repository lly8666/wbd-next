# H1004｜PLAN028 开始真实 Go TLS lane 代际施工

2026-11-03用户已批准PLAN028。H1003修正三处开工歧义；本笔开始产品代码，不重复H1000审计。

- V4EpochStore只在显式AllowLaneReplacement时允许认证的同账号/同tunnel/同epoch旧A与新B同lane重叠；仍只允许一个pending、最多两个已提交实例，默认保持拒绝重复lane。
- 每次真实TLS admission在受保护reply前产生独立随机incarnation，密钥仍走原TLS exporter；失败候选不占位。ReleaseLaneInstance必须匹配account/tunnel/lane/epoch/incarnation。发生过重叠的lane永久禁用旧的epoch-only ReleaseLane，避免迟到A回收B。
- Linux Normal/Game native Stop从真实ColdSnapshot读取该incarnation，Rust owner和驱动Stop/drain完成后再释放精确Go实例；未启用native A+B，不能让两个owner同时争读现有TUN。
- 新增Go真实protected TLS admission测试：A+B/B+C、同账号另一设备不串、第三候选拒绝、重复/错误nonce回滚和旧generation精确回收。测试SOURCE需以随后Action实际结果为准。

**范围限定**：这是首个真实产品源码切片，尚无单端口多client shared Rust IO/新网络路径原生回连，PLAN028整体未完成。027A H998真实在线物理MTU缩窄FAIL、ARM64 Game4FEC Action FAIL、远端ICMP未测和CPU因果未证保留，外层MTU仍默认1460。后续先补共享accept/Rust IP索引分发及其两端fixture，然后再开启A+B native owner。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"Original authenticated V4 epoch overlap and Linux Normal/Game Stop exact generation code started; complete shared native product remains NOT_RUN."}
```
