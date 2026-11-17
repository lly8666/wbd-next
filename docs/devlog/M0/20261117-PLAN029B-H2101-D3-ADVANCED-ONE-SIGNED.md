# PLAN029B H2101｜复用成熟D3，多A高级CN FakeIP单场签名验证

H2100 `SOURCE=4a0b4efe6d0d05f29411fe3816382edebca12b68` [Action44081559353](https://github.com/lly8666/wbd-next/actions/runs/44081559353) Governance/Feature catalog **SUCCESS**，原dns-split-ipv6功能卡压缩至16,284字节，保留所有有真实SOURCE的历史PASS/FAIL，以及H2098当前普通CN真双DNS/Tunnel/TCP/Stop `PASS_SCOPED`。没有再重跑H2098。

029B B2高级CN仍需真原生验证。H2101只复用**现有**H1808/D3单一真实签名Normal夹具`[plan029-v3-real-d3-multia]`：它同时选择CI专用原Rust V3高级CN路径、Direct场景和两A映射，独立原Windows AF_INET CN CNAME→两真实海外A→两不同已持久发布FakeIP，真实Linux物理DNS/Direct UDP、Direct TCP32KiB FIN及原Tunnel TCP/UDP和owned Stop均按原严格oracle验。新增一条廉价路径回归，明确它不会误选B2普通真实A或老029其它强度场景。本次提交一个显式原生marker，不触发028/弱网矩阵。

**资格限定**：这条是`GITHUB_ACTIONS=true`原有签名trial先进映射，不是WinForms/Go canonical `cn-domain-direct=true`用户导入保存/迁移场景；旧缓存重连、Game入口、真实IPv6和同VM10Mbps资源/p99仍NOT_RUN。实际Action/ZIP与原source hash未返回前记NOT_RUN，不把历史H1808绿灯替换新SOURCE证明。

```feature-impact
{"kind":"none","ids":[],"reason":"H2101 test-only existing signed D3 advanced CNAME-two-A/FakeIP regression gate and original SOURCE/cursor request; no product or feature card semantics changed"}
```
