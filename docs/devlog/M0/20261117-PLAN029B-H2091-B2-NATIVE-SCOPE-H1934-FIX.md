# PLAN029B H2091｜将普通CN B2独立签名场景加入严格范围选择器

H2090 `SOURCE=63985588e613bda4c76c743b2b15a9a9e7aca263` [Action44059476705](https://github.com/lly8666/wbd-next/actions/runs/44059476705) cheap、Windows Go、Windows/Linux Rust通过，但真正签名 `native-public-two-os` 被判为纯夹具差异而**SKIPPED**：H2090工作流已有`[plan029b-b2-cn-ordinary-real]`明确试验标记和默认1460配置，但中央`tools/m0_native_ci_scope.py::EXPLICIT_NATIVE_MARKERS`尚只承认B0，原签名job不应偷偷假跑。H2091把唯一B2标记加到该精确白名单，单测断言：B2显式源码触发原生，其他夹具默认不触发。未增加任何旧028/029 P1/P2大场。

H2090 [governance Action44059476683](https://github.com/lly8666/wbd-next/actions/runs/44059476683) **Governance PASS**（H2090精简固定START_HERE热集成功），Feature catalog结构自身`feature-check.json=PASS`，但同job后续旧`test_same_real_tunnel_alias_and_rule_scale`仅匹配三路`if p029_direct or p029_p1_policy or p029_game4_cn:`字符串，而B2实际复用**同一个既有受管Linux TUN别名**，不新建入口。H2091把旧fixture期待加上`or p029b_b2`并保留P1四腿、CN/4096规则与后续旧产品检查，产品源不变。

**不可冒充PASS**：H2089 `d0dd9f1` Action44056378053签名B0真实Winsock UDP/TCP53 A TTL2、AAAA NODATA零上游泄漏及双端Stop独立PASS_SCOPED；H2090 B2因为原生被跳过仍NOT_RUN。H2091准备首次真正B2当前SOURCE原始Windows2025/WSL2 CN物理DNS与同海外IP双Tunnel业务/Stop；历史H2083无V3导出FAIL保留。全部029B B0–B5未完成，不开028/030。

```feature-impact
{"kind":"none","ids":[],"reason":"H2091 only native scope selector marker, historic P1 alias assertion and evidence; no production Rust/Go network/GUI feature changes"}
```
