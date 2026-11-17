# PLAN029B H2102｜旧Wintun RX量子跳包公平性与all/off冷Direct容量

H2101 [Action44082170661](https://github.com/lly8666/wbd-next/actions/runs/44082170661) 独立高级CN原签名D3 `SOURCE=b7bbec854c0926c6003dd369f3195b8b73374d31` 仍在途，固定其SHA不覆盖、不重派。H2102新增的是**另一个受影响产品路径**，将由原工作流的Native路径门决定运行，不重复H2101多A场景。

现有 `wbd-platform::WintunRx::read` 首字节IPv6/非IPv4返回`ReadResult::Skipped`并释放ring；但Rust `v4_windows_native_runtime::stage_sources` 原先仅`ReadResult::Frame`令`captured++`，对`Skipped`只记rejected。TX原逻辑以`captured==BATCH`判断`still_ready`/后续等待；整批IPv6被处理却误认为没有工作，使后续队列中的合法IPv4延迟。修复严格只在Skipp​​ed分支加`captured+=1`；不复制IPv6字节、不开新模块/worker、无Go逐包、保留原4×BATCH公平封顶。Rust单测检查满跳包/混合包量子，便宜Python既有IPv6-route测试加入对真实生产分支的精确断言，原Wintun loan IPv6→IPv4单测继续沿用。**这些不是实际IPv6 Windows应用发包的证据**。

B0另一处：`m0Plan029ColdSource` 曾在判断`route-mode=all`之前验证`DirectFlowHard`，即使`split-enable=false`也可被历史保存的无效Direct cap卡住Rust公共DNS/Tunnel起网。现在先选实际mode，只有活动业务分流才检查Direct cap≤16384；all/off维持既有有界默认值供**DNS用途**TCP53合约，无业务Direct actor/FakeIP；公共DNS地址、MTU、generation及其错误仍拒绝。Go Windows测试覆盖off/all保存极端无效Direct cap、失效CN文件、公共DNS缺失拒绝，以及活动Direct容量越界拒绝。

源码/Go+Rust+便宜Python组件、原`dns-split-ipv6`功能卡同批修改，实际Windows完整Stop只能按H2102独立Action证据；真正IPv6 packet/route/外口、Game与GUI迁移及同VM 10Mbps CPU/p99继续NOT_RUN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H2102 fix original Rust Wintun skipped non-IPv4 receive fairness quantum and Go off/all inactive Direct cap admission; retain independent DNS/padding with tests; genuine IPv6 packets remain NOT_RUN"}
```
