# H2188｜H2186双ISA真网已PASS后，仅修H2187功能卡与热读取治理失败

H2186真正产品SOURCE `e174235872d32cca69bf921fb59904f9bcaee889`：[Action44278039887](https://github.com/lly8666/wbd-next/actions/runs/44278039887) 2原生ISA x86_64/aarch64各8场，16/16原Go TLS/Rust/Linux AF_PACKET/TUN真TCP/UDP与Stop **completed SUCCESS**，原产物SHA与完整项目见[签名机读证据](../evidence/M0/PLAN029-H2186-LINUX-X86-ARM64-EIGHT-CROSSPLATFORM-NATIVE-PASS-20261118.json)。H2187签名/功能卡资料已提交[4455578](https://github.com/lly8666/wbd-next/commit/44555786294a09c3353c99344308de09dd879da1)，但后续[治理Action44279833383](https://github.com/lly8666/wbd-next/actions/runs/44279833383) **FAIL**：4份长期积累的功能卡加入同源证据超过`tools/feature_catalog.py`每卡16384字节硬上限；[maintenance44279833392](https://github.com/lly8666/wbd-next/actions/runs/44279833392) **FAIL**：`governance.py` combined M0 hot read 33771B 超过政策32768B，导致既有负向测试在预算门提前失败。保留失败Action不篡改。

本次只处理文档/目录版式和冗余史料展示，不修改**任何Go/Rust生产实现、测试夹具、原H2186真实签名SOURCE、二进制摘要或已PASS的kernel记录**。4张卡`game-fixed-fec`、`outer-opportunistic-repair`、`path-mtu-budget`、`linux-raw-tun`从冗长缩进JSON改为合法紧凑JSON，部分历史scope描述取其原事件首尾并保留原`status`、`platform`简述、`source_sha`、`evidence`和全部entry；完整旧文仍可由原commit [4455578](https://github.com/lly8666/wbd-next/commit/44555786294a09c3353c99344308de09dd879da1)及更早签名原artifact核查，不重写过去历史资格。单卡目标都小于16384B，M0 cursor与START_HERE只删除重复叙述、缩短hot text，签名证据与主线OPEN和显式未接线范围均保留。复测只限gov+maintenance，不重复H2186网络矩阵；只在CI完成后宣布治理PASS。

仍区分：Linux Game2/4随机startup-padding off/tls/flows有真实raw复制PASS，Linux Normal/Fixed/Auto tls/flows、无离线route-key在线X25519未接线；manual动态物理MTU和实体ARM、跨ISA实际DUT、CPU/p99/压测均未在H2186验；029/029B整体技术OPEN、030尚未启动。

```feature-impact
{"kind":"updated","ids":["game-fixed-fec","outer-opportunistic-repair","path-mtu-budget","linux-raw-tun"],"reason":"Compact historical verification narrative/JSON formatting to satisfy per-card 16KiB and M0 32768B hot-read governance limits while preserving every prior status, source_sha, evidence pointer and current signed H2186 qualification; no product or original native test changes."}
```

## H2189｜H2188 CI结果回收（2026-11-18）

在H2188文档SOURCE [`7157d601`](https://github.com/lly8666/wbd-next/commit/7157d60170df9b084a1eff264651a4c1f9855371) 上，治理 [Action 44281530635](https://github.com/lly8666/wbd-next/actions/runs/44281530635) **completed SUCCESS**，原`Governance`与`Feature catalog`两个jobs均success；[maintenance 44281530588](https://github.com/lly8666/wbd-next/actions/runs/44281530588) **completed SUCCESS**，`regression` job success。H2187 `4455578` 的两个失败Action `44279833383` / `44279833392` 原样保留；此回收只证实功能卡及治理门恢复通过，**不意味着新的产品业务/网络测试**，也不重写 H2186 native 产品SOURCE `e174235872d32cca69bf921fb59904f9bcaee889` 及其16/16签名资格。当前 GitHub Actions 查询时 in_progress/queued 均0；029B/029日常限域PASS_SCOPED，029完整技术出口仍OPEN，030未启动。

**H2189 first receipt write [Action 44284948709](https://github.com/lly8666/wbd-next/actions/runs/44284948709) FAIL**: `structure.json` reports `combined hot byte budget exceeded: 32942` (limit `32768`); Feature catalog semantic/declaration check itself PASS; 121 auxiliary tests PASS. This is cursor text growth, not H2186 native product regression. H2190 shortens cursor; preserve the original failed Action and await the new governance result.

**H2190 verified recovery**: [Action 44285388183](https://github.com/lly8666/wbd-next/actions/runs/44285388183), SOURCE `1b26f2e87f6aa148e97e3b897cea78e6488daeb9`, `Governance` and `Feature catalog` both **completed SUCCESS**. The preceding H2189 FAIL remains recorded, and no product/network retest occurred; H2186 SOURCE remains `e174235872d32cca69bf921fb59904f9bcaee889`. 029/029B user-normal scope PASS_SCOPED, full technical exit OPEN.

**H2191 [Action 44285633983](https://github.com/lly8666/wbd-next/actions/runs/44285633983) FAIL**, `structure.json`: `verified cursor lacks reviewed PASS evidence`. The H2186 JSON is genuinely signed `PASS_SCOPED` rather than the governance hard gate's literal `result=PASS` with `artifact_verified=true`; full 029 technical exit is OPEN. H2192 returns cursor `unverified=true` rather than fabricating or promoting a reviewed PASS. This does not negate the independently successful H2190 governance Action.
