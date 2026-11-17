# WBD Next｜main 接续

**当前：029B。** [PR35](https://github.com/lly8666/wbd-next/pull/35)非冲突设计已合入，依据[029B提示](docs/prompts/M0-PLAN029B.md)与[方案](docs/decisions/M0-PLAN029B-OPTIONAL-SPLIT-FAKEIP-IPV6-20261116.md)施工。028保留限域FAIL、不重开多Wintun/旧矩阵；030未开。029旧H2077仅`PASS_SCOPED`。

**实时资格只看最新main、[M0 cursor](.governance/workstreams/M0/cursor.json)和实际Action产物。** H2088真签名Win2025 Wintun/Npcap↔WSL2 Normal/业务分流OFF的TLS、OS Applied、双向内核TCP/UDP、Stop通过；H2089同源签名应用UDP/TCP53真实A TTL2及本地AAAA空答、上游AAAA=0也`PASS_SCOPED`。B2普通/高级CN、B3物理IPv6、B4全GUI、B5性能A/B仍按各自回执，不能借旧PASS。H2083缺V3 DLL导出真FAIL保留。

**接续：**读[AGENTS](AGENTS.md)、[章程](PROJECT_CHARTER.md)、[M0提示](docs/prompts/M0.md)、[registry](.governance/registry.json)和cursor；先收在途Actions。M0单写main、不覆盖未知提交；一同源Go/Rust/GUI装配，核产品hash、真实驱动和owned WAL Stop，不重复相同网测。

**硬门：**[TLS](docs/architecture/TLS_HANDSHAKE_CONTRACT.md) ClientHello前无私有前导；[MTU](docs/architecture/MTU_CONTRACT.md)用户外层默认**1460B**，1500仅显式，内层Rust预算+OS读回。029B业务Direct关闭不影响原Rust V3公共DNS/Tunnel/padding；新CN默认真实A，显式高级才FakeIP，旧缺键保留语义。未测不作PASS。历史：[027](docs/evidence/M0/PLAN027-H920-SCOPED-CLOSEOUT-20261102.json)/[027A](docs/evidence/M0/PLAN027A-H998-USER-ACCEPTED-SCOPED-CLOSEOUT-20261103.json)/[028](docs/testing/PLAN028_INTEGRATION_ACCEPTANCE.md)，[功能卡](docs/features/README.md)。
