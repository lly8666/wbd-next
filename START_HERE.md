# WBD Next｜main 接续

**当前：029B/029日常用户范围已H2137限域PASS，完整技术出口仍OPEN；无新原生Action、030未开。** [PR35](https://github.com/lly8666/wbd-next/pull/35)非冲突设计已合入，依据[029B提示](docs/prompts/M0-PLAN029B.md)与[方案](docs/decisions/M0-PLAN029B-OPTIONAL-SPLIT-FAKEIP-IPV6-20261116.md)施工。028保留限域FAIL、不重开多Wintun/旧矩阵；030未开。029旧H2077仅`PASS_SCOPED`。

**实时资格只看最新main、[M0 cursor](.governance/workstreams/M0/cursor.json)及签名Action产物。** B0–B3普通/高级CN、AAAA与受管IPv6+IPv4，B4三代真WinForms/Stop [44198794225](https://github.com/lly8666/wbd-next/actions/runs/44198794225)，Game4四lane [44197717052](https://github.com/lly8666/wbd-next/actions/runs/44197717052)，B5同VM双向10Mbps [44201457211](https://github.com/lly8666/wbd-next/actions/runs/44201457211)均各自SOURCE限域原生PASS。B5 CPU/GiB B比A单样本+8.31%，不宣称有收益/持续退化；小TCP p99/P-B2/全宿主IPv6/Game2 split非验收或不支持。旧H2083等FAIL保留，完整技术出口与D1–D5/P1–P2仍OPEN。

**接续：**读[AGENTS](AGENTS.md)、[章程](PROJECT_CHARTER.md)、[M0提示](docs/prompts/M0.md)、[registry](.governance/registry.json)和cursor；先收在途Actions。M0单写main、不覆盖未知提交；一同源Go/Rust/GUI装配，核产品hash、真实驱动和owned WAL Stop，不重复相同网测。

**硬门：**[TLS](docs/architecture/TLS_HANDSHAKE_CONTRACT.md) ClientHello前无私有前导；[MTU](docs/architecture/MTU_CONTRACT.md)用户外层默认**1460B**，1500仅显式，内层Rust预算+OS读回。029B业务Direct关闭不影响原Rust V3公共DNS/Tunnel/padding；新CN默认真实A，显式高级才FakeIP，旧缺键保留语义。未测不作PASS。历史：[027](docs/evidence/M0/PLAN027-H920-SCOPED-CLOSEOUT-20261102.json)/[027A](docs/evidence/M0/PLAN027A-H998-USER-ACCEPTED-SCOPED-CLOSEOUT-20261103.json)/[028](docs/testing/PLAN028_INTEGRATION_ACCEPTANCE.md)，[功能卡](docs/features/README.md)。
