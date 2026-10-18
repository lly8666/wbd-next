# M0 2026-10-18：R0-023 安全先行与下一阶段产品接线图

本页记录 2026-10-18 实际工位快照和本轮 M0 原本已经授权的 R0-023 安全演进。**这是协作/产品依赖顺序，不是新分配或 G3 产品范围变更**；控制权威仍是 main registry，动态进度以分支 cursor、SOURCE 和 Actions 为准。不要凭本页将 worker 标 idle、FEC2 ON 或产品通过。

## 实际工位快照（2026-10-18）

| 角色 | 本轮任务 | 精确交付 CODE / 事实 | 动态缺口 |
|---|---|---|---|
| M0 | R0-M0-V4-PROTECTED-OWNER-COMMIT-023 | 原实 Go↔Rust 1370/1728B LINK 双向两片 SOURCE 821962b7，run39089250014 PASS；新源 dd01c86b 封包前整包分片 M1 slab 预备待 Actions | 2048B 原TUN入口与单轮32条上限、Stop/MTU收缩、原驱动 prefix/unknown、同一真实产品持续业务硬门未收口 |
| M1 | R5-M1-FEC2-OWNER-SCHEDULING-014 | CODE 3f78a671，worker-native39082738345 130/130 PASS，H19 `blocked` | 最新中央 scope/H19 未确认为 PASS；M0 真组合与成本 NOT_RUN，无新独占代码障碍 |
| M2 | R2-M2-AUTHENTICATED-REPAIR-INGRESS-WORKPACK-010 | CODE 654a3c12，worker-native39045616456 70/70 PASS，H25 `ready_for_integration` | Go 原认证、M1 frozen arena、M4 prefix/uncertain live edge 未由 M0 接线 |
| M3 | R5-M3-FEC2-CODEC-NATIVE-017 | CODE8cc5b06d，worker标量122/0/1；M0 Linux x64 true ISA-L F2 11/11 PASS及同机400000编码+e4恢复/腿合格 CPU 窗 SOURCE f088ca04 run39090941413 | worker H/治理、完整ARM64/Windows新 V2 codec 源码原生校验仍需区分；模块微基准≠产品 |
| M4 | R5-M4-FEC2-COLD-POLICY-PLATFORMS-014 | CODE 7cef7e84，原Go冷策略8/8；Linux x64/ARM64/Windows safe-wrapper各2/2，H21 `ready_for_integration` | 产品真实 CLI/GUI/配置生效 ACK、Rust FEC2控制 admit、Windows loader/应用级全链路 NOT_RUN |

## 依赖优先级：剩余的是产品端到端门，不是5个独立工作包的百分比

1. **P0：R0 正常/off 原路径安全收口。** 唯一 Go 认证→Rust 原owner→M4 raw/TUN 主路径；跨轮次大合法 UDP、一个片发出后 MTU变小不能混 stride、前缀/不确定内核完成、Stop归还 loans、可运行持续业务、已知 DATA 丢失后小包不 HOL。保持FEC2 off。先充分收口后续共用的生命周期/路由不变量，避免FEC新功能叠加到脆弱的基础。
2. **P1：仅对已经交付的 worker 组件分阶段整合。** M1 三class、Game shared sender、M2 receipt/frozen/repair和 M3 codec 在原owner类型及原 M4 driver lease 上运行；从真实 Go V4 拿认证、generation/epoch/方向上下文。先完整 functional/资源界，不急于启配置开关。失败按归属回交负责工位的具体反例，不重复分配已完成包。
3. **P2：FEC2 一次受保护能力协商+真实路径。** 建实 source10/repair12/k1..16/r<=20 与原 AEAD/PN、LINK/FrameBudget、M1 首源/期限/parity、M2 authenticated receipt；FEC2 bit2/kind2/3 从预留变实际只能在 hard gate 后按双方独立能力启用，默认仍 OFF。证明确实接过 Rust FEC2，非仅跑 Go policy replay 或 x64 microbench。
4. **P3：Go 唯一配置/产品入口。** M4 七档/两方向auto、一客户端一个 applied revision，接原 CLI/GUI/参数目录、reload/fallback/rollback、旧设迁移与用户实际看到的模式一致；Game只 fixed/off，禁止auto静默打开。Linux/ARM64/Windows safe wrapper 构建不代表 V2 Windows loader/product PASS。
5. **P4：完整业务路径与恢复/Game 回归。** Normal fixed/off/auto、Game2/4 的真实多客户端/双向、稀疏首发/来源、parity公平与shadow重传10%独立账本、真实 Lost DATA、换代重连/未知syscall outcome/IPv6默认处理、DNS/LAN/分流迁移清单。旧版80s中断风险保留R6。
6. **P5：真实复用构建与基线/性能资格。** 按 TEST_PLAN 第0、2、3节：Linux Normal/off真实TUN/raw独立业务10Mbps/方向、热身10s测60s且 CPU/rss/actual injected/first delivered/drop完整；之后必要 RTT/loss、FEC2 N1/N2/N30/50/100、Game 3Mbps 与容量阶梯，不在不够容量主机盲冲500Mbps。对相同 workload 比成本必须同VM同SOURCE AB/BA，绝不能用 codec 57x 直接推产品吞吐。
7. **P6：可交付与物理验收。** 可运行的目标平台/安装、GUI服务启停、与原控制迁移行为逐项验收，实际 Linux ARM64/Windows codec-native和完整装载链、R6长时/80s风险、真实物理500Mbps另列，不因 Actions 部分绿色关闭资格。

以上7项是**剩余产品验收关口分类**，不是7个要新派工位的任务、更不是严格线性排程。可在基础/合同就绪后合理并行开展小的独立平台/恢复反例；总体阻塞链是 **R0 安全原路径 → M1/M2/M3/M4 实际组合 → 正式双方协议/配置生效 → 持续业务/弱网/三目标/发布资格**。可见的“工位空闲”主要是 M2/M4 模块已交接待 M0，并非“产品开发只剩最后5%”。

## 2026-10-18 · M3 H37 验收与单一 G2 中央 Scope 标准

M3 精确 HEAD `41ef0e29c9029949136fe54169f6628eca01fdfa` 由自身 [Governance39094273613](https://github.com/lly8666/wbd-next/actions/runs/39094273613) attempt1 SUCCESS；M0 中央 [run39095544653](https://github.com/lly8666/wbd-next/actions/runs/39095544653) 精确主线 `37d0e43c5327a5bf2f59fb028bd05398e8eb6d05` 的 **M3 job117581113937 SUCCESS**，同时 M1/M2 也通过。**该run整体FAIL** 是 M4 单独的额外 evidence 结果字符串误判，不能写成整run PASS。CODE8cc 原生 Linux x64 真实 ISA-L F2 11/11、40万/腿 k16r16 L1202、e4 recovery 同VM ABBA CPU 合格、M3 独立两个 ZIP 与十个成员 SHA256 复核已经可作为 **M3 scoped codec 组件接入验收**；不得由此关闭 Linux ARM64/Windows x64 完整 M3 新 V2 codec native、Go Windows loader、实际 FEC-on、p99/物理资格。worker H37 仍为 `partial`，不擅改 M3 branch/cursor/epoch。详见 [M0精确验收回执](../../evidence/M0/M0-M3-017-scoped-acceptance-unified-G2-2026-10-18.json)。

新主线中央 `tools/scope_audit.py` 移除了独立的64增量检查与第二套检查点范围判定，直接复用原 M0/G2 `tools/worker_scope_ci.py.audit_worker_history` 的冻结 `G2_BASE`、最多512提交、80条/页、完整 SHA/顺序/页数/每提交完整路径/受审历史合并。中央另外只核实时 main registry、cursor 结构与前后来源祖先，不用 M4 的 MAIN-only context_ref 或 PASS_SCOPED 组件文字另造角色拒绝。旧 `scope-checkpoints.json` 留历史，policy64仍属 standalone `governance.py audit` 有界交接诊断、不再约束中央 Scope。Actions 精确 [governance-maintenance39095981610](https://github.com/lly8666/wbd-next/actions/runs/39095981610) SOURCE `39ea51ea507b00dd88330af7a1c9ea4545ab42f5` SUCCESS（治理回归全部 Actions），中心历史扫描在同一 M3 SOURCE 的先前 `37d0...` 有确切 PASS。

**配额教训**：过渡期多次主线 push 同时触发四条 G2 全历史扫描，短时间用尽 GitHub Actions API（403 remaining=0），部分后续 main Governance/central run 因环境配额 FAIL，非算法或真实scope越权。随后将 `scope-audit.yml` 改为**仅 worker Governance completed 的单一工位精确 SOURCE**运行中央重扫；主线治理工具 push 走既有 maintenance 自动自测，不再无意义地四重重复扫描。不能把 API rate-limited 的控制run改称 PASS，也不因此撤回以前的真实M3 scoped成功收据。下一步仍按原R0-023 的跨轮次大 UDP、MTU中途变化、原driver未知完成/Stop，之后 FEC2 真实 Go认证→Rust owner 集中接线并排缺少的跨平台完整 native 门。

## 本轮快速主线集成：M3 + M4 + M1 实码进 main，M1→M3 首段直接组合

不再从不同 worker 的实时HEAD临时拼产品证据：将 M3 CODE8cc `fec_v2.rs` / 原测试、M4 CODE7cef `fec_v2_policy.go` / 原测试、M1 CODE3f78 `runtime/fec2_owner.rs` / 原测试共六份文件逐一照原 SHA **Git blob完全相同**并入 main，分别注册到现有 codec/engine 模块，保留主线锁定的Cargo/native ISA-L依赖、老V1记录、原Go TLS/ABI/路由。原 Go 冷策略工作流由“复制M4 worker clone”改为“直接复制 main overlay 并在a7a82db原Go realityfront真实包编译测试”；另新增精确主线 codec 真ISA-L入口，无需再跑原40万块4腿微基准。所有 FEC2 能力、kind2/3、真实配置启用仍 **OFF**。

再引入 M0 `crates/wbd-engine/src/fec2_staged.rs`，用真实M1 bounded Arena/3class ParityJob 的冻结源引用构建 M3 单个 `PreparedBlock`，每轮最多4条repair、实际策略轮廓不符则PN前拒绝，`r_sent` 仅由外部传输确定前缀确认后登记；真实源码负例一条源在cauchy中丢失后被M3 scalar e1 精确恢复。**这是内存内组件组合，暂不含原Go认证/KDF、AEAD/PN发射、M4 raw/TUN实际FEC传输、M2真实receipt。** 不写“双端FEC-on已成功”。

精确功能证据：
- 主线 [run39096791296](https://github.com/lly8666/wbd-next/actions/runs/39096791296) SOURCE f50c2d7 真官方 ISA-L V2 codec **11/11 PASS**，对源码主线native而非worker临时覆写；
- [run39096875504](https://github.com/lly8666/wbd-next/actions/runs/39096875504) SOURCE bdfbd5 主线M4 Go冷策略，在真实钉定原Go包 **8/8 PASS**；
- [run39097343657](https://github.com/lly8666/wbd-next/actions/runs/39097343657) 源 `1395d9c5477ae7097fef2aedaaa5630253266da0` native-functional engine **129 PASS、0 FAIL、1 ignored**，包含M1 12个FEC2调度反例及M0真Arena→Cauchy→e1恢复新反例；其他selected kernel/normal/receipt/fec组SUCCESS；
- 同 SOURCE [run39097343616](https://github.com/lly8666/wbd-next/actions/runs/39097343616) 原真实Go TLS→Rust normal/off raw/TUN build+consume **SUCCESS**，原Normal/off双向10Mbps 10s+60s仍仅开发诊断；
- 同 SOURCE R0原生ABI39097343599、G2 bootstrap39097343596、cross-ABI39097343554 SUCCESS。源138之前一次遗漏M1 tests致rust test编译失败，补入原M1文件而非绕过断言；CODEC旧240s红灯（run39096586112）仍保留且未误称全项目/旧codec资格。

[M0 SOURCE1395完整证据](../../evidence/M0/M0-023-FEC2-main-3worker-staged-1395d9c5477ae7097fef2aedaaa5630253266da0.json)。下一批优先对接原Go单次受保护admission→Rust能力/kind2/3、M1首发parity到原M4真实发送和原M2 authenticated repair；原023 65KiB大UDP跨轮次/Stop/MTU/不确定内核完成仍未结，不以新增组件PASS冒充产品资格。ARM64/Windows完整FEC2、UI真实applied、Game、弱网与物理另验。用户要求提速，不再重复旧M3 ISA-L 400k基准。
