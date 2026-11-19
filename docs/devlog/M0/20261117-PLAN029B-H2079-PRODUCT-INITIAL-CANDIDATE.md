# PLAN029B H2079｜真实产品分流/域名/IPv6 DNS/CLI/GUI接线第一批候选

当前主线按已合入 PR35 的最新 `docs/prompts/M0-PLAN029B.md` 新增**实际** Rust、Go、原Windows CLI+GUI装配源码：029B的公共 Rust V3 Tunnel/单DNS/原TLS/正常padding 不因 `split-enable=false` 回退旧V2；关闭/all无Direct UDP actor、CN Trie/FakeIP writer/多余OS业务直连前缀，保留每代OS/WAL Stop。CN普通（新默认 `cn-domain-direct=false`）只将CN域名DNS发唯一物理dns.direct，返回经过验证的真实A/CNAME/TTL，后续业务按真正IP决策；高级true才用原FakeIP受管journal。当前 owner内任意受管 UDP/TCP53 AAAA本地 NOERROR/NODATA（不查任一上游）。Rust/Go C cold ABI 升版本2共136B，外V3共352B；与原Go产物所有装配原hash一一匹配后才增新patch并重算结果blob。原GUI便携旧profiles/导入缺键->true，新Profiles和CLI无配置false，显式false不覆盖。原WFP/TLS/认证Stop或老Normal H2077证据完全不改。

**STATUS CANDIDATE / NOT_RUN。** 下步由源码触发 Windows Go build/Windows Rust ABI/组件测试及Linux Rust，失败只修明确第一编译边界。随后仍需B0真正无Direct业务NAT的TCP53监听、Windows IPv6真实Wintun接入与环境回执、B4 GUI实际effective和B5同VM小型A/B＋受影响旧Normal签名场；未拿到这些不声称029B收口。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6","gui-config-feedback","startup-flow-padding"],"reason":"H2079 actual Go/Rust/GUI source candidate for split off, ordinary CN vs advanced FakeIP, managed AAAA; new source CI/physical NOT_RUN"}
```
