# PLAN029 H1713｜真实Windows应用DNS53→Rust QNAME分流→独立Linux DNS→持久FakeIP→实际Direct UDP

- [H1712 M0-WIN-LINUX](https://github.com/lly8666/wbd-next/actions/runs/43367189032) 源 `6ce01a62b50f53ad890a2c29f1058501b667c63c` Windows328、Linux303 Rust library PASS（4项真实临时文件/批量sync_data/重启恢复/损坏拒绝/真实合成Fake DNS字节测试）；对应[治理与功能卡](https://github.com/lly8666/wbd-next/actions/runs/43367189015)都PASS。旧M0公开链路其他Action FAIL仍按原分层保留。
- H1713一条**新签名Windows2025 + 真Ubuntu WSL2独立Linux内核**单场景，不再本机echo。复制已证H1704原Go PnP/DAD /Wintun /generation /Rust exclusive loan /owned Stop结构：真实Windows应用向测试DNS IP 198.18.87.88:53发送 `www.cn.example` A DNS查询，系统Owned /32进Wintun Rust唯一RX。Rust `PacketIngress` 按QNAME判CN且DNS用途先于IP，`DnsPending`保存原client ID/tuple，物理绑定源IPv4+IP_UNICAST_IF连接独立Linux UDP46098，Linux DNS给真实CNAME edge.cdn.example A=其独立guest IP，Rust校验上游来源/QNAME/ID并从真实portable文件batch sync得到可公告FakeIP，`synthesize_cn_a`构造只含Fake A的DNS答复回原Windows应用。
- 应用真实读取FakeIP，再向这个FakeIP:46111发业务UDP（没有Go稳态逐包泵）；固定一条FakeIP池/24 owned route保证Wintun捕获，Rust依据Fake→真实guest元组Direct、物理绑定另一个UDP socket送独立Linux 46111，Linux回真实字节，Rust生成原Fake源地址IPv4 UDP回包并立即提交Wintun，原Windows应用必须收到。只允许一条owned Linux HyperV入站规则覆盖46098与46111，Stop原Go loan/lease/两条测试owned route、rule，并上传SOURCE/真实失败stage。
- **范围严格**：Linux guest A是172.16/12同宿主vEthernet LAN，不能冒充“CN域名解析海外”D2、也不是公网物理机器；这个Action只证明CN DNS直接来源、Fake持久化/业务直连，**不验证非CN/Tunnel DNS真出口**。仍是仅 `m0_v4_probe` 显式测试ABI，非正式TLS/Normal/Game4产品。真实只在Action结果/Stop证据达标后给部分PASS，不从代码推断。
- 后续必做正式一Rust入口装配、两DNS用途强制与同endpoint TCP53、非CN共享CDN实际隧道、Normal/Game4、迁移/GUI/MTU1460、startup-padding和D1-D5/P1-P2。028已H1657限定收口，030未自动开工。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Collect H1712 Win/Linux real filesystem FakeIP journal unit PASS and add one real signed Windows Wintun CN QNAME physical Linux DNS->durable FakeIP->original application Direct UDP business network scene."}
```
