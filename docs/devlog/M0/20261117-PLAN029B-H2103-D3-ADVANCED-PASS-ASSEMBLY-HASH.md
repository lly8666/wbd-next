# PLAN029B H2103｜高级CN原签名PASS入原功能卡，修H2102装配首错

H2101 SOURCE `b7bbec854c0926c6003dd369f3195b8b73374d31` [Action44082170661](https://github.com/lly8666/wbd-next/actions/runs/44082170661) 原Windows2025 Npcap/Wintun↔WSL2 Linux真实Normal整体SUCCESS。原ZIP artifact14327264772 SHA256 `fff7d0f2060acdefbf69741b8b272523acb2cd1fbd2af6551af5ae1ca4fff2e2`，4组SOURCE完全相同，DLL SHA256 `bfe9aed16dad1578e3494433c8282b1c0d42ab100ec9db4983ea8c55a66189d4`。真实CN CNAME→多A→两不同FakeIP `198.18.0.1`、`198.18.0.2`；单次物理DNS上游，原Win内核Wintun→物理Direct UDP真实回显；原Direct TCP32,768B双端回显及半关闭、正常Tunnel UDP/Windows→Linux TCP和owned Stop PASS。后者并非028反向TCP。**限域为CI高级CN FakeIP数据面**，正式WinForms `cn-domain-direct`保存/旧缺键迁移/重连仍NOT_RUN。H2098普通CN另一SOURCE真实A与Tunnel出口已独立通过，不跨实际出口比较CPU。

H2102 SOURCE `dae37c6fa6438d158c9e89bd3731143a307181ea` [Action44084190869](https://github.com/lly8666/wbd-next/actions/runs/44084190869)、Win CLI [44084191001](https://github.com/lly8666/wbd-next/actions/runs/44084191001)、GUI [44084190889](https://github.com/lly8666/wbd-next/actions/runs/44084190889) **FAIL**；共同首错`prepare_windows_wiring.py --check-only`读取同一旧装配 manifest `result_blob` 与实际已更新冷Go文件不符。原产品Rust及Go源码和单元测试未因此回滚；原Windows签名数据面本轮**NOT_RUN**。H2103只更新该manifest中两处预期blob：冷Go文件 `42131ff2855556c6c01a27a42dd5863848d51b2e`、配套Go测试`0c51df873d1adc6d975f7c684934c6347f0218fc`。保持原donor/其它ABI/装配，新增独立H2102 FAIL证据，H2101高级CN PASS写原`dns-split-ipv6`卡（压缩旧无SOURCE全局IPv6占位，但真实IPv6 NOT_RUN留limitations，所有有SOURCE历史项保留）。

本次`[m0-native-smoke]`限定一个新SOURCE原Normal/off真实签名回归，验证H2102 Go冷cap和Rust公平调整无其他退化，不开弱网/028矩阵；若没有真正发IPv6并证明路由/接管，不能宣称B3已PASS。GUI配置/多代Stop/Game/B5同VM10Mbps CPU、真实交付GiB、RSS/唤醒和小流p99仍需独立取证。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H2103 update two frozen Windows Go assembly manifest result_blob hashes for H2102 cold source/tests; collect independently source-pinned H2101 advanced CNAME multi-A FakeIP signed proof in bounded original card; preserve all historic real-SOURCE verification"}
```
