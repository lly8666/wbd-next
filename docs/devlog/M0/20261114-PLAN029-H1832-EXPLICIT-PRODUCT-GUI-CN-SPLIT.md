# PLAN029 H1832｜真签名异步FakeIP D3收口＋正式CN分流配置接线

- [H1831 Action43585387611](https://github.com/lly8666/wbd-next/actions/runs/43585387611) 在SOURCE `268fdc150937416a51991b440a961a5dc96a1a3e`真实Windows2025签名Npcap+Wintun、原Go TLS/Rust V3、WSL2 Ubuntu：CN CNAME→2A→两个不同FakeIP（198.18.0.1/.2），Linux见真实物理Direct DNS/UDP，Windows原应用收到物理业务回包，Tunnel及D2非CN→CN IP分流代表，owned Stop均PASS_SCOPED。日志显示`WBD_PLAN029_D3_MULTIA_SCENE=1`，而`P2_MIXED_SCENE=0`；不能用旧workflow标题`no-scene`误判。DNS首次应用回答531ms、发送1次，只是端到端时长不等于fsync独立延迟。见`docs/evidence/M0/PLAN029-H1832-H1831-SIGNED-ASYNC-D3-MULTIA-20261114.json`。
- 现行029主机入口`m0Plan029TrialCold`仍有`GITHUB_ACTIONS=true`＋`WBD_PLAN029_NATIVE_V3_TRIAL=1`双条件：这种旧CI-only gate错误阻止真实用户启用，产品真实API/OS已可施工，不能等旧实测全PASS才开放。
- **H1832实现候选**：`m0NativeV4Options`增加`SplitEnable`、`CNRulesFile`，原M0 Go原生入口支持`--split-enable`（默认false，保持非分流老路径）和`--cn-rules-file`（在CN模式必填有效本机绝对文件，冷读且拒绝符号链接/空文件）。明确启动并于新一代有效配置启用的分流不需要GitHub Actions变量；老Action试验marker仍可source-locked使用。实际Go原生OS Apply/Rust owner/Ready/Stop不做假值，Game2/4未接到`NativeSplitWorker`时显式失败、不给伪Applied；Normal/Fixed/Auto保持原选路/FEC载体。
- **GUI同批**：装配manifest新增`split-enable`复选和`cn-rules-file`便携相对输入提示，保存仍是下次连接生效；`PortableStore.Effective`将rules路径规范化至受控目录内绝对路径，`ImportValues`对外部导入先按当前目录校验/有界复制成data内源文件。实际生成CLI flag/参数目录/GUI labels同源构建，锚点与新Git结果blob已在提交前逐项本地演算验证。缺少CN域名库的`include/regexp`仍明确拒绝，不用逆DNS/SNI欺骗CDN。
- **当前验证边界**：H1832的新代码/GUI来源在本次提交时所有原Windows Go/GUI compiler与真产品起停均**NOT_RUN**，真实用户正式模式开启且Readback并未通过；本提交非交付。H1831真D3证据只适用于268 SOURCE。剩余异步TCP53/慢磁盘HOL/compaction interrupted recovery、Direct 1MiB约22倍慢、P1 CPU、Game4 CN、GUI真Connect Stop/IPv6等保持OPEN。读新SOURCE自动CI再对症修；不重复D3、028矩阵或造第二个Git writer。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Add explicit production non-CI next-connection split opt-in and portable CN rules settings through original Go CLI and GUI manifest, preserving actual-OS Ready and fail-closed Game2/4; signed D3 current-source receipt added but new public wiring not yet network verified."}
```
